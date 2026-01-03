#!/usr/bin/env python3
"""
Network Traffic Capture Script for Axon

Captures HTTP/HTTPS network traffic on a Linux box and logs it to JSON format
for later import into Axon's D1 database.

Requirements:
    pip install scapy geoip2 maxminddb-geolite2

Usage:
    sudo python3 capture_traffic.py [options]

Options:
    --interface <iface>   Network interface to capture on (default: auto-detect)
    --output <file>       Output JSON file (default: traffic_capture.json)
    --filter <filter>     BPF filter (default: 'tcp port 80 or tcp port 443')
    --count <n>           Number of packets to capture (default: unlimited)
    --verbose             Enable verbose output
"""

import argparse
import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional
import logging

try:
    from scapy.all import sniff, IP, TCP, Raw, get_if_list
    from scapy.layers.http import HTTPRequest, HTTP
except ImportError:
    print("Error: scapy is not installed. Run: pip install scapy", file=sys.stderr)
    sys.exit(1)

try:
    from maxminddb import open_database
    from maxminddb.const import MODE_AUTO
    import maxminddb
    GEOIP_AVAILABLE = True
except ImportError:
    print("Warning: maxminddb not installed. Country detection disabled.", file=sys.stderr)
    print("To enable: pip install geoip2 maxminddb-geolite2", file=sys.stderr)
    GEOIP_AVAILABLE = False


class TrafficCapture:
    """Captures and logs network traffic to JSON format."""

    def __init__(self, output_file: str = "traffic_capture.json", verbose: bool = False):
        self.output_file = output_file
        self.verbose = verbose
        self.traffic_log: List[Dict] = []
        self.packet_count = 0

        # Setup logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

        # Setup GeoIP if available
        self.geoip_reader = None
        if GEOIP_AVAILABLE:
            try:
                from maxminddb.const import MODE_AUTO
                # Try to use system GeoLite2 database
                geoip_paths = [
                    '/usr/share/GeoIP/GeoLite2-Country.mmdb',
                    '/var/lib/GeoIP/GeoLite2-Country.mmdb',
                    './GeoLite2-Country.mmdb'
                ]
                for path in geoip_paths:
                    try:
                        self.geoip_reader = open_database(path, MODE_AUTO)
                        self.logger.info(f"GeoIP database loaded from: {path}")
                        break
                    except FileNotFoundError:
                        continue

                if not self.geoip_reader:
                    self.logger.warning("GeoIP database not found. Country detection disabled.")
            except Exception as e:
                self.logger.warning(f"Failed to load GeoIP database: {e}")

    def get_country_code(self, ip: str) -> Optional[str]:
        """Get country code from IP address using GeoIP."""
        if not self.geoip_reader:
            return None

        try:
            result = self.geoip_reader.get(ip)
            if result and 'country' in result:
                return result['country'].get('iso_code', None)
        except Exception as e:
            self.logger.debug(f"GeoIP lookup failed for {ip}: {e}")

        return None

    def extract_http_info(self, packet) -> Optional[Dict]:
        """Extract HTTP information from packet."""
        if not packet.haslayer(IP):
            return None

        ip_layer = packet[IP]
        src_ip = ip_layer.src
        dst_ip = ip_layer.dst

        # Try to extract HTTP request information
        path = "/"
        method = "UNKNOWN"
        user_agent = None
        host = None

        # Check if packet has HTTP layer (scapy)
        if packet.haslayer(HTTPRequest):
            http = packet[HTTPRequest]
            method = http.Method.decode('utf-8', errors='ignore') if http.Method else "GET"
            path = http.Path.decode('utf-8', errors='ignore') if http.Path else "/"
            host = http.Host.decode('utf-8', errors='ignore') if http.Host else None
            user_agent = http.User_Agent.decode('utf-8', errors='ignore') if http.User_Agent else None

        # Fallback: Try to parse raw HTTP data
        elif packet.haslayer(Raw):
            try:
                payload = packet[Raw].load.decode('utf-8', errors='ignore')
                lines = payload.split('\r\n')

                if lines and len(lines) > 0:
                    # Parse request line (e.g., "GET /path HTTP/1.1")
                    request_line = lines[0].split(' ')
                    if len(request_line) >= 2:
                        method = request_line[0]
                        path = request_line[1]

                    # Parse headers
                    for line in lines[1:]:
                        if ': ' in line:
                            header, value = line.split(': ', 1)
                            if header.lower() == 'user-agent':
                                user_agent = value
                            elif header.lower() == 'host':
                                host = value
            except Exception as e:
                self.logger.debug(f"Failed to parse raw HTTP: {e}")

        # Skip if we couldn't extract meaningful HTTP data
        if method == "UNKNOWN":
            return None

        # Build full URL if we have host
        if host:
            full_path = f"http://{host}{path}"
        else:
            full_path = path

        # Get country code
        country = self.get_country_code(src_ip)

        # Create traffic entry matching Axon schema
        traffic_entry = {
            "timestamp": int(time.time() * 1000),  # Milliseconds since epoch
            "path": full_path,
            "method": method,
            "ip": src_ip,
            "country": country,
            "user_agent": user_agent or "Unknown",
            "prediction": "unknown",  # Will be classified by Axon later
            "confidence": 0.0,
            "bot_score": None,
            "created_at": datetime.utcnow().isoformat() + 'Z'
        }

        return traffic_entry

    def packet_handler(self, packet):
        """Handle captured packet."""
        self.packet_count += 1

        if self.verbose and self.packet_count % 10 == 0:
            self.logger.debug(f"Processed {self.packet_count} packets...")

        # Extract HTTP information
        traffic_entry = self.extract_http_info(packet)

        if traffic_entry:
            self.traffic_log.append(traffic_entry)

            if self.verbose:
                self.logger.info(
                    f"Captured: {traffic_entry['method']} {traffic_entry['path']} "
                    f"from {traffic_entry['ip']} ({traffic_entry['country'] or 'Unknown'})"
                )

            # Save periodically (every 10 entries)
            if len(self.traffic_log) % 10 == 0:
                self.save_to_file()

    def save_to_file(self):
        """Save captured traffic to JSON file."""
        try:
            with open(self.output_file, 'w') as f:
                json.dump(self.traffic_log, f, indent=2)

            if self.verbose:
                self.logger.debug(f"Saved {len(self.traffic_log)} entries to {self.output_file}")
        except Exception as e:
            self.logger.error(f"Failed to save to file: {e}")

    def start_capture(self, interface: Optional[str] = None,
                     bpf_filter: str = "tcp port 80 or tcp port 443",
                     count: int = 0):
        """Start capturing network traffic."""
        self.logger.info(f"Starting traffic capture...")
        self.logger.info(f"Interface: {interface or 'auto-detect'}")
        self.logger.info(f"Filter: {bpf_filter}")
        self.logger.info(f"Output: {self.output_file}")
        self.logger.info(f"Count: {count if count > 0 else 'unlimited'}")
        self.logger.info(f"Press Ctrl+C to stop...\n")

        try:
            # Start packet capture
            sniff(
                iface=interface,
                filter=bpf_filter,
                prn=self.packet_handler,
                store=False,
                count=count
            )
        except KeyboardInterrupt:
            self.logger.info("\nCapture stopped by user")
        except PermissionError:
            self.logger.error("Permission denied. This script requires root/sudo privileges.")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Capture error: {e}")
            sys.exit(1)
        finally:
            # Final save
            self.save_to_file()
            self.logger.info(f"\nCapture complete!")
            self.logger.info(f"Total packets processed: {self.packet_count}")
            self.logger.info(f"HTTP requests captured: {len(self.traffic_log)}")
            self.logger.info(f"Output saved to: {self.output_file}")

    def __del__(self):
        """Cleanup: close GeoIP reader."""
        if self.geoip_reader:
            try:
                self.geoip_reader.close()
            except:
                pass


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Capture network traffic and log to JSON for Axon",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--interface', '-i',
        type=str,
        default=None,
        help='Network interface to capture on (default: auto-detect)'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        default='traffic_capture.json',
        help='Output JSON file (default: traffic_capture.json)'
    )

    parser.add_argument(
        '--filter', '-f',
        type=str,
        default='tcp port 80 or tcp port 443',
        help='BPF filter (default: "tcp port 80 or tcp port 443")'
    )

    parser.add_argument(
        '--count', '-c',
        type=int,
        default=0,
        help='Number of packets to capture (default: unlimited)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '--list-interfaces',
        action='store_true',
        help='List available network interfaces and exit'
    )

    args = parser.parse_args()

    # List interfaces if requested
    if args.list_interfaces:
        print("Available network interfaces:")
        for iface in get_if_list():
            print(f"  - {iface}")
        sys.exit(0)

    # Check for root privileges
    if sys.platform.startswith('linux') and os.geteuid() != 0:
        print("Warning: This script typically requires root privileges on Linux.", file=sys.stderr)
        print("Run with: sudo python3 capture_traffic.py", file=sys.stderr)

    # Start capture
    capture = TrafficCapture(output_file=args.output, verbose=args.verbose)
    capture.start_capture(
        interface=args.interface,
        bpf_filter=args.filter,
        count=args.count
    )


if __name__ == '__main__':
    import os
    main()
