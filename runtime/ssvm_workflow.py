import warnings
from time import sleep
import FeatureCloud.api.cli.test.commands as fc
import pandas as pd
import os
import zipfile
import time

warnings.simplefilter(action='ignore', category=FutureWarning)


def delete_ds_store_files(path: str):
    for root, dirs, files in os.walk(path):
        for file in files:
            if file == '.DS_Store':
                fullpath = os.path.abspath(os.path.join(root, file))
                os.remove(fullpath)


def run_workflow(app_images: list[str], data_dir: str, generic_dir: str, results_path: str,
                 controller_host: str = 'http://localhost:8000', channel: str = 'local',
                 query_interval: int or float = 1):
    print(f'Run workflow {app_images}')
    for app_image in app_images:
        if app_image == 'featurecloud.ai/basic_normalization':
            dataset = results_path.split("/")[-2]
            n_clients = results_path.split("/")[-1]
        elif app_image == 'featurecloud.ai/fc_survival_svm':
            dataset = results_path.split("/")[-3]
            n_clients = results_path.split("/")[-2]
        elif app_image == 'featurecloud.ai/fc_survival_evaluation':
            dataset = results_path.split("/")[-4]
            n_clients = results_path.split("/")[-3]

        test_id = run_app(app_image, results_path, controller_host, channel, query_interval, data_dir, generic_dir)
        instances = check_finished(test_id, controller_host, app_image)
        results_path = f'{results_path}/{app_image.split("/")[1]}'
        i = 0
        try:
            move_results(results_path, instances, test_id, data_dir)
        except FileNotFoundError:
            if i <= 10:
                sleep(10)
            else:
                raise FileNotFoundError
        print('')
        sleep(1)
    print(f'Workflow run {app_images} finished.')


def run_app(app_image: str, input_dir: str, controller_host: str, channel: str, query_interval: int or float,
            data_dir: str,
            generic_dir: str):
    print(f'Run app {app_image}')
    client_dirs = []
    for it in os.scandir(input_dir):
        if it.is_dir():
            if "client_" in str(it.path).split("/")[-1]:
                client_dirs.append(str(it.path).replace(data_dir, '')[1:])
    client_dirs = ",".join(client_dirs)
    test_id = fc.start(controller_host=controller_host, client_dirs=client_dirs,
                       generic_dir=generic_dir, app_image=app_image, channel=channel, query_interval=query_interval,
                       download_results="./")

    return test_id


def check_finished(test_id: str or int, controller_host: str, app_image: str):
    # print('Waiting for test to be finished...')
    finished = False
    df = None
    times = []
    start_time = time.time()
    while not finished:
        df = fc.info(test_id=test_id, format='dataframe', controller_host=controller_host)
        if df.loc[test_id, 'status'] == 'finished' or df.loc[test_id, 'status'] == 'error':
            finished = True
            print(f'Test {test_id} finished')
            rec_time = time.time() - start_time
            times.append([app_image, dataset, n_clients, rec_time])
            times_df = pd.DataFrame(times)
            times_df.to_csv(f'times_{app_image.split("/")[1]}_{dataset}_{n_clients}_{subfolder}.csv', index=False)
        else:
            sleep(1)
    return df.loc[test_id, 'instances']


def move_results(results_path: str, instances: pd.DataFrame, test_id: str or int, data_dir: str):
    print('Move results...')
    os.makedirs(results_path, exist_ok=True)
    for instance in instances:
        client_dir = results_path + f'/client_{instance["id"] + 1}'
        filename = f'results_test_{test_id}_client_{instance["id"]}_{instance["name"]}'
        os.makedirs(client_dir, exist_ok=True)
        filepath = data_dir + "/tests/" + filename + ".zip"
        with zipfile.ZipFile(filepath, 'r') as zip_ref:
            zip_ref.extractall(client_dir)
        sleep(10)
        while not os.path.exists(client_dir):
            sleep(20)
        # os.remove(data_dir + "/tests/" + filename + ".zip")


# all images need to be pulled first and exist locally
app_images = ['featurecloud.ai/basic_normalization',
              'featurecloud.ai/fc_survival_svm',
              'featurecloud.ai/fc_survival_evaluation'
              ]

# data directory of the FeatureCloud controllercontroller
data_dir = '../'
subfolder = 'federated'

# contains the config file for all clients
generic_dir = f'tests/{subfolder}/generic'

controller_host = 'http://192.168.2.159:8000'

# this example runs the analysis on the data in data_dir/dataset/n_clients
for dataset in ['brca',
                'gbsg2',
                'whas500',
                'microbiome']:
    for n_clients in [1, 3, 5]:
        print(f'Run dataset {dataset} for {n_clients} clients')
        input_path = f'{data_dir}/tests/{subfolder}/{dataset}/{n_clients}_clients'
        delete_ds_store_files(input_path)
        run_workflow(app_images=app_images, data_dir=data_dir, generic_dir=generic_dir, results_path=input_path,
                     controller_host=controller_host)
        sleep(1)
        print(f'Finished run dataset {dataset} for {n_clients} clients')
        print('')
        print('')
    sleep(1)

print("Workflow Completed.")
