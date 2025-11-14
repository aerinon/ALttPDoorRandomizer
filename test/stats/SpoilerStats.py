import os
import sys
import csv
import collections


def process_file(file_path):
    items_at_locations = collections.defaultdict(list)
    with open(file_path, 'r') as file:
        location_section = False
        for line in file:
            line = line.strip()
            if 'Locations:' in line:
                location_section = True
            elif 'Shops:' in line:
                location_section = False
            elif location_section and line:
                location, item = line.split(":")
                if 'Bottle' in item:
                    item = 'Bottle'
                items_at_locations[location].append(item.strip())
    return items_at_locations


def process_directory(directory_path):
    all_items_at_locations = collections.defaultdict(list)
    for file_name in os.listdir(directory_path):
        if file_name.endswith('.txt'):
            file_path = os.path.join(directory_path, file_name)
            items_at_locations = process_file(file_path)
            for location, items in items_at_locations.items():
                all_items_at_locations[location].extend(items)
    return all_items_at_locations


def write_to_csv(items_at_locations, csv_file_path):
    # Get a list of all unique items across all locations
    all_items = set(item for items in items_at_locations.values() for item in items)

    with open(csv_file_path, 'w', newline='') as file:
        writer = csv.writer(file)
        # Write the header row
        writer.writerow(['Location'] + sorted(list(all_items)))
        # Write a row for each location
        for location in sorted(items_at_locations.keys()):
            item_counts = collections.Counter(items_at_locations[location])
            # Only write non-zero counts
            row = [location]
            for item in sorted(all_items):
                count = item_counts.get(item, 0)
                row.append(count if count > 0 else '')  # Empty string instead of 0
            writer.writerow(row)

if __name__ == '__main__':
    input_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join('..', '..', 'test_games', 'stats')
    output_path = os.path.join(input_dir, 'output.csv')

    items_at_locations = process_directory(input_dir)
    write_to_csv(items_at_locations, output_path)