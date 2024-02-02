import socket
import threading
import time
import argparse
import re
import sys

BUFFER_SIZE = 1000

def handle_client(client_socket, address, multiplier):
    # Initialize received_bytes and start_time variables
    received_bytes = 0
    start_time = time.time()

    try:
        while True:
            # Receive data from client
            data = client_socket.recv(BUFFER_SIZE)
            # If "BYE" is received from client, exit loop
            if "BYE" in data.decode():
                break
            #Add received data length to received_bytes variable
            received_bytes += len(data)
       
    except Exception as e:
        # Print exception message if an error occurs while handling the client connection     
        print(f"Exception while handling client connection {address}: {e}")     

    # Calculate end_time, duration, transfer_size, and rate variables
    end_time = time.time()
    duration = end_time - start_time
    transfer_size = received_bytes / multiplier
    rate = (received_bytes / duration) * 8 / 1000000

    # Print client connection information (IP, port, duration, transfer size, and transfer rate)
    print(f'ID              Interval     Received        Rate')
    print(f'{address[0]}:{address[1]}     0.0 - {duration:.1f}       {transfer_size:.2f} MB         {rate:.2f} Mbps')

    # Send acknowledgement message to client
    client_socket.send(b'ACK')


    # Close client socket connection
    client_socket.close()

# The Server function
def server(args):
    host = args.bind
    port = args.port
    allowed_formats = ['B', 'KB', 'MB']
    format = args.format

    # If the 'format' argument is invalid, print error message and return from function
    if format not in allowed_formats:
        print(f"Invalid format argument. Allowed formats: {', '.join(allowed_formats)}")
        return

    # Calculate the multiplier based on the 'format' value
    multiplier = 1000 ** allowed_formats.index(format)

    # Create a new 'socket' object for the server
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Bind the server socket to the specified 'host' and 'port'
        server_socket.bind((host, port))
    except Exception as e:
        #Print error message if the bind operation fails and return from function
            print(f"Bind failed. Error: {e}")
            return

    #  Set the server to listen for incoming connections
    server_socket.listen(5)

    # Print a message to the console indicating that the server is listening
    print(f"A simpleperf server is listening on port {port}")

    # Continuously accept incoming connections and create a new thread to handle each connection
    while True:
        # Wait for a client to connect, accept the connection
        client_socket, address = server_socket.accept()
        # Print a message indicating that a client is connected
        print(f"A simpleperf client with {address[0]}:{address[1]} is connected with {host}:{port}")
        # Create a new thread to handle the client connection
        client_thread = threading.Thread(target=handle_client, args=(client_socket, address, multiplier))
        client_thread.start()

# The client function
def client(args):
    # Retrieve 'serverip', 'port', 'format' arguments from the 'args' parameter
    host, port, format = args.serverip, args.port, args.format
    # Check if the 'format' argument is valid, if not print error message and return from function
    valid_formats = {'B', 'KB', 'MB'}
    if format not in valid_formats:
        print(f'Invalid format argument. Allowed formats: {", ".join(valid_formats)}')
        return
    #Calculate the multiplier based on the 'format' value
    multiplier = {'B': 1, 'KB': 1000, 'MB': 1000**2}[format]

    # Retrieve 'time' and 'interval' arguments from the 'args' parameter
    total_duration, interval_time = args.time, args.interval
    start_time = time.time()
    # Initialize variables for tracking the amount of data sent
    total_bytes_sent, bytes_per_interval = 0, 0

    # Create a socket and connect to the server
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    # Print message indicating that client is connected to server.
    print(f'Client connected with {host} port {port}')


    if interval_time != 0:
        # Calculate the number of intervals based on total duration and interval time
        intervals = total_duration // interval_time
        # Keep track of previous interval's end time

        prev_interval_end_time = start_time
        # Start timer
        timer = time.time()
        # Loop over each interval
        for i in range(intervals + 1):
                # Start time of the interval
            interval_start_time = time.time()
                # Number of bytes sent in the interval
            bytes_per_interval = 0
            # Send data for the duration of the interval
            while time.time() - interval_start_time < interval_time:
                data = bytes(BUFFER_SIZE)
                client_socket.send(data)
                bytes_per_interval += len(data)
            # End time of the interval
            interval_end_time = time.time()
            # Duration of the interval
            interval_duration = interval_end_time - interval_start_time
            # Calculate the rate for the interval
            interval_rate = (bytes_per_interval / interval_duration) * 8 / 1000000
            # Print the statistics for the interval
            print(f'ID              Interval     Transfer        Rate')
            print(f'{host}:{port}     {prev_interval_end_time - timer:.1f} - {interval_end_time - timer:.1f}       {bytes_per_interval/multiplier:.2f} {format}         {interval_rate:.2f} Mbps')
                # Update the previous interval end time
            prev_interval_end_time = interval_end_time
            # Update the total bytes sent
            total_bytes_sent += bytes_per_interval
            
        # Send BYE message and close the socket
        client_socket.send(b'BYE')
        client_socket.recv(BUFFER_SIZE)
        client_socket.close()
        # Print total statistics for the intervals
        print(f'-' * 10)
        print(f'Total Interval: {start_time - timer:.1f} - {interval_end_time - timer:.1f}')
        print(f'Total Transfer: {total_bytes_sent/multiplier:.2f} {format}')
        # Calculate total duration
        total_duration = interval_end_time - start_time
        # Calculate total rate
        total_rate = (total_bytes_sent / total_duration) * 8 / 1000000
        print(f'Total Rate: {total_rate:.2f} Mbps')

    else:
            # Send data for the duration of the test
        while time.time() - start_time < total_duration:
            data = bytes(BUFFER_SIZE)
            client_socket.send(data)
            total_bytes_sent += len(data)
            # Send BYE message and close the socket
        client_socket.send(b'BYE')
        client_socket.recv(BUFFER_SIZE)
        client_socket.close()

        end_time = time.time()
        duration = end_time - start_time
        # Calculate transfer size, duration, and rate
        transfer_size = total_bytes_sent / multiplier
        rate = (total_bytes_sent / duration) * 8 / 1000000
        # Print the statistics
        print('-' * 80)
        print(f'ID                          Interval              Transfer            Bandwidth')
        print(f'{host}:{port}             0.0 - {duration:.1f}             {transfer_size:.2f} MB       {rate:.2f} Mbps')
        print('-' * 80)

    if args.num:
        num = args.num
        # Extract the numeric value and unit of the transfer size from the 'num' argument
        match = re.match(r"([0-9]+)([a-z]+)", num, re.I)
        if not match:
                # Print an error message if the 'num' argument is not in the correct format
                print('Invalid num argument. Usage: --num<number><unit>')
                return

        num, unit = match.groups()
        # Convert the unit to a multiplier based on the allowed formats
        unit_multiplier = {'B': 1, 'KB': 1000, 'MB': 1000000}[unit.upper()]
        # Calculate the total transfer size based on the numeric value and unit multiplier
        transfer_size = int(num) * unit_multiplier
        # Loop until the total bytes sent matches the transfer size
        while total_bytes_sent < transfer_size:
            # Generate a data payload of size BUFFER_SIZE and send it to the server
            data = bytes(BUFFER_SIZE)
            client_socket.send(data)
            # Add the size of the payload to the total bytes sent
            total_bytes_sent += len(data)
            # Send a 'BYE' message to the server to indicate that the transfer is complete
        client_socket.send(b'BYE')
        client_socket.recv(BUFFER_SIZE)
        client_socket.close()
            # Calculate and print the transfer statistics
        end_time = time.time()
        duration = end_time - start_time

        rate = (transfer_size / duration) * 8 / 1000000
        transfer_size = transfer_size / multiplier

        print('-' * 80)
        print(f'     ID               Interval          Transfer          Bandwidth')
        print(f'{host}:{port}       0.0 - {duration:.1f}       {transfer_size:.2f} {format}         {rate:.2f} Mbps')
        print('-' * 80)   

def main():
    # Set up an argument parser to handle command line arguments
    parser = argparse.ArgumentParser(description='A simplified version of iperf using sockets.')

    # Add command line arguments for server/client mode, IP address, port, duration, etc.
    parser.add_argument('-s', '--server', action='store_true', help='Start in server mode')
    parser.add_argument('-c', '--client', action='store_true', help='Start in client mode')
    parser.add_argument('-b', '--bind', default='127.0.0.1', help='Specify the IP address to bind to')
    parser.add_argument('-I', '--serverip', help='Specify the IP address of the server to connect to')
    parser.add_argument('-p', '--port', type=int, default=8088, help='Specify the port number to use')
    parser.add_argument('-t', '--time', type=int, default=10, help=' Set the duration of the test in seconds')
    parser.add_argument('-P', '--parallel', type=int, help='Set the number of parallel connections to use')
    parser.add_argument('-f', '--format', choices=['B', 'KB', 'MB'], default='MB', help='Set the transfer rate format')
    parser.add_argument('-n', '--num', metavar="<number><unit>", help='Specify the number of times to send message')
    parser.add_argument('-i', '--interval', type=int, default=0, help='Sepecify the interval to print results (in seconds)')

    
    args = parser.parse_args()
    parallel = args.parallel

    # Check if both server and client modes are specified
    if args.server and args.client:
        print('Error: cannot specify both server and client mode')
        return

    # Check if either server or client mode is specified
    if not args.server and not args.client:
        print('Error: must specify either server or client mode')
        return

    # Call the server() function if server mode is enabled
    if args.server:
        server(args)

    # Call the client() function if client mode is enabled
    if args.client:
        if parallel:
            #If the parallel argument is specified, start multiple threads for the client function
            for i in range(parallel):
                # Create a new thread and start it with the client function as the target and the parsed arguments as the argument
                p = threading.Thread(target = client, args= (args, ))
                p.start()
        else:
            client(args)

# Call the main function if this script is being run directly
if __name__ == '__main__':
    main() 



