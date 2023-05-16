#nodeport loadbalancer yml -- Tamás amerika np 5001?
#két serverre sok kliens aztán kilő
#python pandas
#iperf test a terminálban is, megvárni mindent, nodeport nincs out-of-order?

import subprocess
import time
import argparse
import pandas as pd
import datetime
import re

DEFAULT_INTERVAL = "1"
DEFAULT_BANDWITH = "1g"
DEFAULT_TIME = "5"
DEFAULT_LENGTH ="100"
DEFAULT_COUNT = "2"
DEFAULT_PLACE = "2"
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
            lb_ip = subprocess.run(['kubectl', '--context', 'mcs-eu', 'get', 'service', 
                                    'iperf-server-loadbalancer', '-o', 'jsonpath={.status.loadBalancer.ingress[0].ip}'], capture_output=True, text=True)
            if lb_ip.stdout.strip() != '':
                external_ip = lb_ip.stdout.strip()
                break
            time.sleep(1)
        
    #nodeport service    
    if service == "2":
        subprocess.call(['kubectl', '--context', 'mcs-eu', 'apply', '-f', 'iperf-server-np.yml'])
        
        #new port instead of 5001, only with local cluster
        if place == "1":
            output = subprocess.check_output(['kubectl', '--context', 'mcs-eu', 'get', 'service', 'iperf-server-nodeport', '-o', 'jsonpath="{.spec.ports[0].nodePort}"'])
            port = output.decode("utf-8").replace('"', '')
        
        #name of the node running the pod
        output = subprocess.check_output(['kubectl', '--context', 'mcs-eu', 'get', 'po', '-l', 'app=iperf-server', '-o', 'jsonpath="{.items[0].spec.nodeName}"'])
        nodeName = output.decode("utf-8").replace('"', '')
        
        #external ip of the node
        output = subprocess.check_output(['kubectl', '--context', 'mcs-eu', 'get', 'nodes', nodeName, '-o', 'jsonpath="{.status.addresses[1].address}"'])
        external_ip = output.decode("utf-8").replace('"', '')
    
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
            output = subprocess.check_output(['kubectl', '--context', 'mcs-am', 'get', 'serviceimports', '-o', 'jsonpath="{.items}"'])
            result = output.decode("utf-8").replace('"', '')
            output = subprocess.check_output(['kubectl', '--context', 'mcs-am', 'get', 'po', '-o', 'jsonpath="{.items[0].status.phase}"'])
            phase = output.decode("utf-8").replace('"', '')
            if result != "[]" and phase == "Running":
                break
            time.sleep(3)
            
        #ip address of the serviceexport
        output = subprocess.check_output(['kubectl', '--context', 'mcs-am', 'get', 'serviceimports', '-o', 'jsonpath="{.items[0].spec.ips[0]}"'])
        mcs_clusterset_ip = output.decode("utf-8").replace('"', '')
        
        #name of the client pod
        output = subprocess.check_output(['kubectl', '--context', 'mcs-am', 'get', 'po', '-o', 'jsonpath="{.items[0].metadata.name}"'])
        client_pod = output.decode("utf-8").replace('"', '')
        
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
    

def cleanup(place, service):

    subprocess.call(['kubectl', '--context', 'mcs-eu', 'delete', '-f','iperf-server.yml'])
    
    if service == "1":
        subprocess.call(['kubectl', '--context', 'mcs-eu', 'delete', '-f', 'iperf-server-lb.yml'])
        
    if service == "2":
        subprocess.call(['kubectl', '--context', 'mcs-eu', 'delete', '-f', 'iperf-server-np.yml'])
        
    if place == "2":
        subprocess.call(['kubectl', '--context', 'mcs-am', 'delete', '-f', 'iperf-client.yml'])
        
        if service == "1":
            subprocess.call(['kubectl', '--context', 'mcs-eu', 'delete', '-f', 'serviceExport_lb.yml'])
        
        if service == "2":
            subprocess.call(['kubectl', '--context', 'mcs-eu', 'delete', '-f', 'serviceExport_np.yml'])
            
    print("\nCleanup complete.\n")

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
    cleanup(args.place, args.service)
