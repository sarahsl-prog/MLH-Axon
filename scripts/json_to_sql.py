#!/usr/bin/env python3
"""
Convert captured traffic JSON to SQL INSERT statements for Axon D1 database.

Usage:
    python3 json_to_sql.py input.json > import.sql
    wrangler d1 execute axon-db --file=import.sql
"""

import json
import sys
import argparse
from typing import List, Dict


def escape_sql_string(value: str) -> str:
    """Escape single quotes in SQL string."""
    if value is None:
        return "NULL"
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def generate_insert_statements(traffic_data: List[Dict]) -> str:
    """Generate SQL INSERT statements from traffic data."""
    if not traffic_data:
        return "-- No data to import"

    sql_statements = []
    sql_statements.append("-- Axon Traffic Data Import")
    sql_statements.append(f"-- Generated: {traffic_data[0].get('created_at', 'unknown')}")
    sql_statements.append(f"-- Records: {len(traffic_data)}\n")

    # Use batch inserts for better performance (100 records per INSERT)
    batch_size = 100
    for i in range(0, len(traffic_data), batch_size):
        batch = traffic_data[i:i + batch_size]

        sql_statements.append(
            "INSERT INTO traffic (timestamp, path, method, ip, country, user_agent, prediction, confidence, bot_score) VALUES"
        )

        values = []
        for entry in batch:
            timestamp = entry.get('timestamp', 0)
            path = escape_sql_string(entry.get('path', '/'))
            method = escape_sql_string(entry.get('method', 'GET'))
            ip = escape_sql_string(entry.get('ip', 'unknown'))
            country = escape_sql_string(entry.get('country')) if entry.get('country') else 'NULL'
            user_agent = escape_sql_string(entry.get('user_agent', 'Unknown'))
            prediction = escape_sql_string(entry.get('prediction', 'unknown'))
            confidence = entry.get('confidence', 0.0)
            bot_score = entry.get('bot_score') if entry.get('bot_score') is not None else 'NULL'

            values.append(
                f"  ({timestamp}, {path}, {method}, {ip}, {country}, {user_agent}, {prediction}, {confidence}, {bot_score})"
            )

        sql_statements.append(',\n'.join(values) + ';')
        sql_statements.append('')  # Empty line between batches

    return '\n'.join(sql_statements)


def main():
    parser = argparse.ArgumentParser(
        description='Convert traffic JSON to SQL INSERT statements'
    )
    parser.add_argument(
        'input_file',
        help='Input JSON file from capture_traffic.py'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output SQL file (default: stdout)'
    )

    args = parser.parse_args()

    # Read JSON data
    try:
        with open(args.input_file, 'r') as f:
            traffic_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate data
    if not isinstance(traffic_data, list):
        print("Error: JSON must be an array of traffic entries", file=sys.stderr)
        sys.exit(1)

    # Generate SQL
    sql_output = generate_insert_statements(traffic_data)

    # Write output
    if args.output:
        try:
            with open(args.output, 'w') as f:
                f.write(sql_output)
            print(f"SQL written to: {args.output}", file=sys.stderr)
        except Exception as e:
            print(f"Error writing output: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(sql_output)


if __name__ == '__main__':
    main()
