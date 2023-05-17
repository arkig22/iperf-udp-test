#nodeport loadbalancer yml -- Tamás amerika np 5001?
#python pandas
#iperf test a terminálban is, nodeport csak néha out-of-order?

import subprocess
import time
import argparse
import datetime
import re

DEFAULT_INTERVAL = "1"
DEFAULT_BANDWITH = "100m"
DEFAULT_TIME = "10"
DEFAULT_LENGTH ="200"
DEFAULT_COUNT = "1"
DEFAULT_PLACE = "1"
DEFAULT_SERVICE = "1"
external_ip = ""
mcs_clusterset_ip = ""
client_pod = ""
port = "5001"
filename = ""

def init(place, service):

    global external_ip
    global mcs_clusterset_ip
    global client_pod
    global port
    
    subprocess.call(['kubectl', '--context', 'mcs-eu', 'apply', '-f', 'iperf-server.yml'])
    
    #loadbalancer service
    if service == "1":
        subprocess.call(['kubectl', '--context', 'mcs-eu', 'apply', '-f', 'iperf-server-lb.yml'])
    
        #wait for the external ip of the service
        while True:
            external_ip = subprocess.check_output(['kubectl', '--context', 'mcs-eu', 'get', 'service', 'iperf-server-loadbalancer', '-o', 'jsonpath={.status.loadBalancer.ingress[0].ip}']).decode("utf-8").replace('"', '')
            if external_ip != '': 
                break
            time.sleep(1)
        
    #nodeport service    
    if service == "2":
        subprocess.call(['kubectl', '--context', 'mcs-eu', 'apply', '-f', 'iperf-server-np.yml'])
        
        #new port instead of 5001, only with local cluster
        if place == "1": 
            port = subprocess.check_output(['kubectl', '--context', 'mcs-eu', 'get', 'service', 'iperf-server-nodeport', '-o', 'jsonpath="{.spec.ports[0].nodePort}"']).decode("utf-8").replace('"', '')
        
        #name of the node running the pod
        nodeName = subprocess.check_output(['kubectl', '--context', 'mcs-eu', 'get', 'po', '-l', 'app=iperf-server', '-o', 'jsonpath="{.items[0].spec.nodeName}"']).decode("utf-8").replace('"', '')
        
        #external ip of the node
        external_ip = subprocess.check_output(['kubectl', '--context', 'mcs-eu', 'get', 'nodes', nodeName, '-o', 'jsonpath="{.status.addresses[1].address}"']).decode("utf-8").replace('"', '')

    #remote client
    if place == "2":

        #client on the remote cluster
        subprocess.call(['kubectl', '--context', 'mcs-am', 'apply', '-f', 'iperf-client.yml'])
        
        #serviceexport according to the type of service
        if service == "1": 
            subprocess.call(['kubectl', '--context', 'mcs-eu', 'apply', '-f', 'serviceExport_lb.yml'])

        if service == "2": 
            subprocess.call(['kubectl', '--context', 'mcs-eu', 'apply', '-f', 'serviceExport_np.yml'])   

        #wait for the serviceimport and the deployment to be created
        while True:
            result = subprocess.check_output(['kubectl', '--context', 'mcs-am', 'get', 'serviceimports', '-o', 'jsonpath="{.items}"']).decode("utf-8").replace('"', '')
            phase = subprocess.check_output(['kubectl', '--context', 'mcs-am', 'get', 'po', '-o', 'jsonpath="{.items[0].status.phase}"']).decode("utf-8").replace('"', '')
            if result != "[]" and phase == "Running": 
                break
            time.sleep(3)
            
        #ip address of the serviceexport
        mcs_clusterset_ip = subprocess.check_output(['kubectl', '--context', 'mcs-am', 'get', 'serviceimports', '-o', 'jsonpath="{.items[0].spec.ips[0]}"']).decode("utf-8").replace('"', '')
        
        #name of the client pod
        client_pod = subprocess.check_output(['kubectl', '--context', 'mcs-am', 'get', 'po', '-o', 'jsonpath="{.items[0].metadata.name}"']).decode("utf-8").replace('"', '')
        
    print("\nTest setup complete.\n")
    time.sleep(5)
    
        
def test(count, place, service):

    global filename
    now = datetime.datetime.now()
    filename = "iperf_results_{}.txt".format(now.strftime("%Y-%m-%d_%H-%M-%S"))

    with open(filename, 'w') as f:
        for i in range(int(count)):

            if place == "1": 
                cmd = ['iperf', '-c', external_ip, '-u', '-i', args.interval, '-b', args.bandwidth, '-l', args.length, '-t', args.time, '-p', port]
            if place == "2": 
                cmd = ["kubectl", "--context", "mcs-am", "exec", "-it", client_pod, "--", "iperf", "-c", mcs_clusterset_ip, "-u", "-i", args.interval, "-b", args.bandwidth, "-l", args.length, "-t", args.time, "-p", port]
            result = subprocess.run(cmd, stdout=subprocess.PIPE)
            output = result.stdout.decode('utf-8')
            print(output)
            f.write(output)    
            time.sleep(2)

    print("\nTest complete.\n")
    
    
def write_result(input_file, output_file):

    with open(input_file, "r") as in_f, open(output_file, "a") as out_f:
        lines = in_f.readlines()
        for i in range(len(lines)):
            if "Server Report" in lines[i]:
                parts = lines[i+2].split()

                int_st, int_end = parts[2].split("-")
                lost, total = parts[10].split("/")
                l_avg, l_min, l_max, l_stdev = parts[12].split("/")
                if args.place == "2":
                    rx, inp = parts[16].split("/")
                    values = [args.place, args.service, args.bandwidth, args.length, int_st, int_end, parts[4], parts[6], parts[8], lost, total, l_avg, l_min, l_max, l_stdev, parts[14], rx, inp, parts[18]]
                if args.place == "1":
                    values = [args.place, args.service, args.bandwidth, args.length, int_st, int_end, parts[4], parts[6], parts[8], lost, total, l_avg, l_min, l_max, l_stdev, parts[14], "", "", parts[16]]
            
                output_line = ','.join(values) + '\n'
                out_f.write(output_line)
    
    
def reset(place, service):
    #deletes every existing resources
    subprocess.call(['kubectl', '--context', 'mcs-eu', 'delete', '-f', 'iperf-server.yml', '-f', 'iperf-server-lb.yml', '-f', 'iperf-server-np.yml', '-f', 'serviceExport_lb.yml', '-f', 'serviceExport_np.yml'], stderr=subprocess.DEVNULL)
    subprocess.call(['kubectl', '--context', 'mcs-am', 'delete', '-f', 'iperf-client.yml'], stderr=subprocess.DEVNULL)
    
    print("\nReset complete.\n")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Run iperf client to measure network bandwidth',formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--interval', '-i', default=DEFAULT_INTERVAL, help='Interval between measurements')
    parser.add_argument('--bandwidth', '-b', default=DEFAULT_BANDWITH, help='Target bandwidth for iperf test')
    parser.add_argument('--time', '-t', default=DEFAULT_TIME, help='Duration of each iperf test')
    parser.add_argument('--length', '-l', default=DEFAULT_LENGTH, help='Packet length for iperf test')
    parser.add_argument('--count', '-c', default=DEFAULT_COUNT, help='Number of measurements to take')
    parser.add_argument('--place', '-p', default=DEFAULT_PLACE, help='Location of the iperf server (1 for local, 2 for remote)')
    parser.add_argument('--service', '-s', default=DEFAULT_SERVICE, help='LoadBalancer or NodePort (1 for LoadBalancer, 2 for NodePort)')
    args = parser.parse_args()

    init(args.place, args.service)
    test(args.count, args.place, args.service)
    write_result(filename, "output.csv")
    answer = input("Do you want to reset? (y/n): ")
    if answer.lower() == "y": 
        reset(args.place, args.service)
