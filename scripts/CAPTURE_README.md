# Network Traffic Capture Script

This script captures HTTP/HTTPS network traffic on a Linux box and logs it to JSON format for import into Axon's D1 database.

## Features

- Captures HTTP/HTTPS traffic using packet sniffing
- Extracts method, path, IP, user-agent, and other metadata
- GeoIP integration for country code detection
- Outputs JSON format compatible with Axon's database schema
- Periodic auto-save to prevent data loss
- Configurable filtering and output options

## Requirements

- **Linux operating system** (requires raw socket access)
- **Root/sudo privileges** (required for packet capture)
- **Python 3.7+**
- **Network interface with traffic** (physical or virtual)

## Installation

### 1. Install Python dependencies

```bash
cd scripts/
pip install -r requirements_capture.txt
```

Or install manually:

```bash
pip install scapy geoip2 maxminddb-geolite2
```

### 2. (Optional) Download GeoIP database

The script will work without GeoIP, but country detection will be disabled.

For better country detection, download the MaxMind GeoLite2 database:

```bash
# Option 1: Use system package manager (Ubuntu/Debian)
sudo apt-get install geoip-database-extra

# Option 2: Download manually
# Register at https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
# Download GeoLite2-Country.mmdb and place in one of:
#   - /usr/share/GeoIP/GeoLite2-Country.mmdb
#   - /var/lib/GeoIP/GeoLite2-Country.mmdb
#   - ./GeoLite2-Country.mmdb (current directory)
```

## Usage

### Basic Usage

Capture traffic and save to default file (`traffic_capture.json`):

```bash
sudo python3 capture_traffic.py
```

### Advanced Options

```bash
# Specify output file
sudo python3 capture_traffic.py --output /tmp/my_traffic.json

# Capture on specific interface
sudo python3 capture_traffic.py --interface eth0

# Capture only 100 packets
sudo python3 capture_traffic.py --count 100

# Use custom BPF filter (capture all TCP traffic)
sudo python3 capture_traffic.py --filter "tcp"

# Capture only HTTP (port 80)
sudo python3 capture_traffic.py --filter "tcp port 80"

# Enable verbose output
sudo python3 capture_traffic.py --verbose

# List available network interfaces
python3 capture_traffic.py --list-interfaces
```

### Complete Example

```bash
sudo python3 capture_traffic.py \
  --interface eth0 \
  --output captured_traffic.json \
  --filter "tcp port 80 or tcp port 443" \
  --count 500 \
  --verbose
```

## Output Format

The script outputs JSON in the following format, compatible with Axon's database schema:

```json
[
  {
    "timestamp": 1704326400000,
    "path": "http://example.com/api/users",
    "method": "GET",
    "ip": "192.168.1.100",
    "country": "US",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
    "prediction": "unknown",
    "confidence": 0.0,
    "bot_score": null,
    "created_at": "2024-01-03T12:00:00Z"
  },
  {
    "timestamp": 1704326401000,
    "path": "/admin/login",
    "method": "POST",
    "ip": "203.0.113.42",
    "country": "CN",
    "user_agent": "curl/7.68.0",
    "prediction": "unknown",
    "confidence": 0.0,
    "bot_score": null,
    "created_at": "2024-01-03T12:00:01Z"
  }
]
```

### Field Descriptions

- **timestamp**: Unix timestamp in milliseconds
- **path**: HTTP request path (or full URL if Host header available)
- **method**: HTTP method (GET, POST, etc.)
- **ip**: Source IP address of the request
- **country**: ISO country code (if GeoIP enabled)
- **user_agent**: User-Agent header value
- **prediction**: Classification result (set to "unknown" for import; Axon will classify)
- **confidence**: Confidence score (0.0 for import data)
- **bot_score**: Cloudflare bot score (null for external captures)
- **created_at**: ISO 8601 timestamp

## Importing into Axon Database

Once you have captured traffic, you can import it into Axon's D1 database:

### Method 1: Using Wrangler D1

```bash
# Prepare import SQL from JSON
python3 json_to_sql.py captured_traffic.json > import.sql

# Import into D1
wrangler d1 execute axon-db --file=import.sql
```

### Method 2: Using CSV Import

```bash
# Convert JSON to CSV
python3 json_to_csv.py captured_traffic.json traffic.csv

# Import CSV into D1
wrangler d1 execute axon-db --command="
  .mode csv
  .import traffic.csv traffic
"
```

### Method 3: Manual SQL Insert

For small datasets, you can manually craft INSERT statements:

```sql
INSERT INTO traffic (timestamp, path, method, ip, country, user_agent, prediction, confidence, bot_score)
VALUES
  (1704326400000, 'http://example.com/api/users', 'GET', '192.168.1.100', 'US', 'Mozilla/5.0...', 'unknown', 0.0, NULL),
  (1704326401000, '/admin/login', 'POST', '203.0.113.42', 'CN', 'curl/7.68.0', 'unknown', 0.0, NULL);
```

## Troubleshooting

### Permission Denied

```
PermissionError: [Errno 1] Operation not permitted
```

**Solution**: Run with sudo privileges:
```bash
sudo python3 capture_traffic.py
```

### No Packets Captured

**Possible causes**:
1. Wrong interface - use `--list-interfaces` to see available interfaces
2. No traffic on specified ports - try broader filter: `--filter "tcp"`
3. Interface not receiving traffic - check with `tcpdump` or `wireshark`

### GeoIP Not Working

```
Warning: maxminddb not installed. Country detection disabled.
```

**Solution**: Install GeoIP libraries:
```bash
pip install geoip2 maxminddb-geolite2
```

### Encrypted HTTPS Traffic

The script can capture HTTPS connections but cannot decrypt the payload without SSL/TLS keys. Only connection metadata (IP, timestamp) will be available for HTTPS.

For full HTTP inspection, consider:
- Setting up a transparent proxy with SSL interception
- Capturing on the server side where traffic is decrypted
- Using application-level logging instead of packet capture

## Security Considerations

- **Privacy**: This script captures network traffic which may contain sensitive data
- **Legal**: Ensure you have authorization to capture traffic on the network
- **Storage**: Captured data should be stored securely and deleted when no longer needed
- **Scope**: Only capture on networks/systems you own or have explicit permission to monitor

## Performance Tips

- Use specific BPF filters to reduce processing overhead
- Capture to SSD/fast storage for high-traffic environments
- Consider using `--count` to limit capture duration
- For production use, consider running as a systemd service with log rotation

## Integration with Axon

This script is designed to complement Axon's edge-based traffic collection:

1. **Axon Worker**: Captures traffic at Cloudflare edge (production traffic)
2. **This Script**: Captures traffic on-premises (development, testing, honeypot)

Both output compatible formats for unified analysis and model training.

## License

This script is part of the Axon project. See LICENSE file for details.
