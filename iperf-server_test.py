#táblázatba végeredmény csak az eredmény adatok csv-be
#nodeport loadbalancer yml -- Tamás
#két serverre sok kliens aztán kilő
#python pandas
#cleanup a végén
#github repo

import subprocess
import time
import argparse
import pandas as pd

DEFAULT_INTERVAL = "1"
DEFAULT_BANDWITH = "1g"
DEFAULT_TIME = "5"
DEFAULT_LENGTH =" 100"
DEFAULT_COUNT = "2"
DEFAULT_PLACE = "1"
DEFAULT_SERVICE = "1"
external_ip = ""
mcs_clusterset_ip = ""
client_pod = ""

def init(place, service):

    global external_ip
    global mcs_clusterset_ip
    global client_pod
    
    subprocess.call(['kubectl', '--context', 'mcs-eu', 'apply', '-f', 'iperf-server.yml'])
    subprocess.call(['kubectl', '--context', 'mcs-eu', 'apply', '-f', 'iperf-server-loadbalancer.yml'])
    
    while True:
        lb_ip = subprocess.run(['kubectl', '--context', 'mcs-eu', 'get', 'service', 'iperf-server-loadbalancer', '-o', 'jsonpath={.status.loadBalancer.ingress[0].ip}'], capture_output=True, text=True)
        if lb_ip.stdout.strip() != '':
            external_ip = lb_ip.stdout.strip()
            break
        time.sleep(1)
        
    if place == "2":
        print("asd")
        subprocess.call(['kubectl', '--context', 'mcs-am', 'apply', '-f', 'iperf-client.yml'])
        
        output = subprocess.check_output(['kubectl', '--context', 'mcs-am', 'get', 'serviceimports', 'iperf-server-loadbalancer', '-o', 'jsonpath="{.spec.ips[0]}"'])
        mcs_clusterset_ip = output.decode("utf-8").replace('"', '')

        output = subprocess.check_output(['kubectl', '--context', 'mcs-am', 'get', 'po', '-o', 'jsonpath="{.items[0].metadata.name}"'])
        client_pod = output.decode("utf-8").replace('"', '')
    
    
def test(count, place, service):

    for i in range(int(count)):
    
            if place == "1":
                cmd = ['iperf', '-c', external_ip, '-u', '-i', args.interval, '-b', args.bandwidth, '-l', args.length, '-t', args.time, '-p', '5001']
            if place == "2":
                cmd = ['kubectl', '--context', 'mcs-am', 'exec', '-it', client_pod, '--', 
                       'iperf', '-c', mcs_clusterset_ip, '-u', '-i', args.interval, '-b', args.bandwidth, '-l', args.length, '-t', args.time, '-p', '5001']
                       
            subprocess.run(cmd)
            time.sleep(2)


def cleanup(place, service):

    subprocess.call(['kubectl', '--context', 'mcs-eu', 'delete', 'deployment','iperf-server'])
    subprocess.call(['kubectl', '--context', 'mcs-eu', 'delete', 'service', 'iperf-server-loadbalancer'])
        
    if place == "2":
        subprocess.call(['kubectl', '--context', 'mcs-am', 'delete', 'deployment', 'iperf-client'])

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
    cleanup(args.place, args.service)
