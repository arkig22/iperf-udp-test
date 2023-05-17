import subprocess
import multiprocessing
import time

def run_iperf(server_ip):
    cmd = ['iperf', '-c', server_ip, '-u', '-t', '60', '-i', '5', '-b', '100m', '-l', '200', '-p', '5001']
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output, _ = process.communicate()
    return output.decode('utf-8')
    
    
def write_result(input_file, output_file):

    with open(input_file, "r") as in_f, open(output_file, "a") as out_f:
        lines = in_f.readlines()
        for i in range(len(lines)):
            if "Server Report" in lines[i]:
                parts = lines[i+2].split()

                int_st, int_end = parts[2].split("-")
                lost, total = parts[10].split("/")
                l_avg, l_min, l_max, l_stdev = parts[12].split("/")
                values = [int_st, int_end, parts[4], parts[6], parts[8], lost, total, l_avg, l_min, l_max, l_stdev, parts[14]]
            
                output_line = ','.join(values) + '\n'
                out_f.write(output_line)

if __name__ == '__main__':
    server_ip = '34.118.121.145'
    num_tests = 75
    results = []

    with open('iperf_results.txt', 'w') as file:
        pool = multiprocessing.Pool(processes=num_tests)

        for _ in range(num_tests):
            result = pool.apply_async(run_iperf, (server_ip,))
            results.append(result)

        time.sleep(40)
        cmd = ['kubectl', 'scale', 'deploy', 'iperf-server', '--replicas=1']
        subprocess.call(cmd)
        pool.close()
        pool.join()

        for result in results:
            file.write(result.get())
    write_result("iperf_results.txt", "scale.csv")
    cmd = ['kubectl', 'scale', 'deploy', 'iperf-server', '--replicas=3']
    subprocess.call(cmd)

