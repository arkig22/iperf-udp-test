# iperf-udp-test

## About The Project

This project provides an easy way to measure UDP traffic in a Kubernetes enviroment on any Cloud Provider network.
The project uses iPerf to test the network and has measuring options for the following cases:
* the iPerf client runs locally, and the server runs on a europen cluster in the cloud
* the iPerf client runs on an american cluster, and the server runs on a european cluster, both in the cloud in a Multi Cluster setup

Your can also choose between LoadBalancer, and NodePort as the Kubernetes Service that exposes the iPerf server.

The results of the tests are written to an externel file, both in txt and csv.

## Getting Started

Because of all the available Cloud Providers on the market right now, and their different setup methods I can't give an exact way of installation,
but regardless I collected all the steps that sum up the setup process.

### Prerequisites

* kubectl
* python3
* iperf v2.0.x
* your Cloud Providers CLI (e.g. gcloud for Google)

### Installation

1. Create two clusters: one in Europe, and in the USA.
2. Configure your MCS enviroment for these two clusters.
3. Connect both of the clusters to kubectl. After this step the new clusters should be present in your Kubernetes config file.
4. Change the context name in the config file for the clusters: mcs-eu for Europe, and mcs-am for America. 
   ```sh
   kubectl config rename-context CURRENT_CONTEXT_NAME mcs-eu/mcs-am
   ```
5. Clone the repo. 

## Usage

Start the program in the root of the repo:
```sh
python3 iperf-server-test.py --YOUR_FLAGS
```

The flags you can set: 

* -h, --help : provides explanation and default values
* -i, --interval : Intervals between reports, same as iPerf v2
* -b, --bandwith : Sets bandwith for the test, same as iPerf v2
* -t, --time : Duration of a test, same as iPerf v2
* -l, --length : Packet length for the test in bytes, same as iPerf v2
* -c, --count : Number of measurements to take
* -p, --place : Location of the iPerf client (1 for EU, 2 for USA)
* -s, --service : Type of service to expose the iPerf server (1 for LoadBalancer, 2 for NodePort)

First the program creates the necessary resources (iPerf server Deployment, LoadBalander Service...) and than starts the measurement.

After the tests are finished you can prompt to erase all created resources or not. 
If you are planning to run multiple tests it is easier, if you only delete after the last one.

The files with the results will be in the repo root.
