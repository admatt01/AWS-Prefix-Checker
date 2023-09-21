#!/usr/bin/python3

import boto3
import ipaddress

def main():
    while True:
        # Get user input for AWS region and VPC ID
        aws_region = input("Enter your AWS region: ")
        vpc_id = input("Enter your VPC ID: ")

        # Initialize Boto3 client for AWS EC2
        ec2_client = boto3.client('ec2', region_name=aws_region)

        # Get user input for the IP prefix (CIDR) to check
        ip_prefix_to_check = input("Enter the IP prefix (CIDR) to check: ")

        # Ask the user if they want to view existing subnets
        view_subnets = input("Would you like to display your VPC's Subnets (Yes/No)? ").strip().lower()
        if view_subnets == 'yes':
            print_existing_subnets(ec2_client, vpc_id)

        # Retrieve the VPC information
        vpc = ec2_client.describe_vpcs(VpcIds=[vpc_id])['Vpcs'][0]
        vpc_cidr = vpc['CidrBlock']

        # Check if the entered prefix is within the VPC's CIDR range
        entered_prefix = ipaddress.IPv4Network(ip_prefix_to_check)
        vpc_network = ipaddress.IPv4Network(vpc_cidr)

        conflicting_subnet_entries = set()  # Initialize a set for subnets here
        conflicting_route_entries = []  # Initialize the list for routes here

        # Check if the entered prefix overlaps with any existing subnets within the VPC
        subnets = ec2_client.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['Subnets']
        existing_subnet_cidrs = [subnet['CidrBlock'] for subnet in subnets]

        # Exclude the VPC CIDR block from the list of existing subnet CIDRs
        existing_subnet_cidrs = [cidr for cidr in existing_subnet_cidrs if cidr != vpc_cidr]

        for existing_cidr in existing_subnet_cidrs:
            existing_subnet = ipaddress.IPv4Network(existing_cidr)
            if entered_prefix.overlaps(existing_subnet):
                print(f"The entered IP prefix {ip_prefix_to_check} overlaps with an existing subnet: {existing_cidr}")
                conflicting_subnet_entries.add(existing_cidr)  # Add the conflicting CIDR

        if not conflicting_subnet_entries and entered_prefix == vpc_network:
            print(f"The entered IP prefix {ip_prefix_to_check} is the VPC CIDR range. Please choose a more specific prefix to test.")
        elif not conflicting_subnet_entries and entered_prefix.subnet_of(vpc_network):
            print(f"The entered IP prefix {ip_prefix_to_check} is within the VPC CIDR range and is available.")
        elif not conflicting_subnet_entries:
            print(f"The entered IP prefix {ip_prefix_to_check} is outside the VPC CIDR range.")

        # Check for overlaps in all route tables and print details if conflicts are found
        route_tables = ec2_client.describe_route_tables(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['RouteTables']

        # Exclude the VPC CIDR block from the list of existing route table CIDRs
        vpc_cidr_network = ipaddress.IPv4Network(vpc_cidr)

        for route_table in route_tables:
            for route in route_table.get('Routes', []):
                if 'DestinationCidrBlock' in route:
                    route_cidr = ipaddress.IPv4Network(route['DestinationCidrBlock'])
                    if entered_prefix.overlaps(route_cidr) and not entered_prefix.subnet_of(vpc_cidr_network):
                        table_id = route_table['RouteTableId']
                        conflicting_route_entries.append(f"Route Table Entry (Table ID: {table_id}): {route_cidr}")

        # Print details of conflicting entries
        if conflicting_subnet_entries:
            print(f"The entered IP prefix {ip_prefix_to_check} conflicts with the following existing subnets:")
            for entry_cidr in conflicting_subnet_entries:
                print(f"Subnet CIDR: {entry_cidr}")

        if conflicting_route_entries:
            print(f"The entered IP prefix {ip_prefix_to_check} conflicts with the following route table entries:")
            for route_entry in conflicting_route_entries:
                print(route_entry)

        # If no conflicts are found, inform the user
        if not conflicting_subnet_entries and not conflicting_route_entries and entered_prefix != vpc_network:
            print(f"The entered IP prefix {ip_prefix_to_check} does not conflict with existing subnets or route table entries.")

        # Ask the user if they want to view route tables
        view_route_tables = input("Would you like to view the route tables (Yes/No)? ").strip().lower()
        if view_route_tables == 'yes':
            print_route_tables(ec2_client, vpc_id)

        # Ask the user if they want to check another prefix
        check_another = input("Would you like to check another prefix (Yes/No)? ").strip().lower()
        if check_another != 'yes':
            break

def print_route_tables(ec2_client, vpc_id):
    route_tables = ec2_client.describe_route_tables(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['RouteTables']

    if not route_tables:
        print("No route tables found for this VPC.")
    else:
        print("Route Tables:")
        for route_table in route_tables:
            print(f"Route Table ID: {route_table['RouteTableId']}")
            print("Destinations:")
            for route in route_table.get('Routes', []):
                if 'DestinationCidrBlock' in route:
                    destination_cidr = route['DestinationCidrBlock']
                    route_status = route.get('State', 'N/A')
                    print(f"- Destination: {destination_cidr}, Status: {route_status}")
            print()

def print_existing_subnets(ec2_client, vpc_id):
    subnets = ec2_client.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['Subnets']

    if not subnets:
        print("No subnets found for this VPC.")
    else:
        print("Existing Subnets:")
        for subnet in subnets:
            print(f"- Subnet ID: {subnet['SubnetId']}, CIDR: {subnet['CidrBlock']}")

if __name__ == "__main__":
    main()
