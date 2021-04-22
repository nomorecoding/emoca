from utils.condor import execute_on_cluster
from pathlib import Path
import train_emodeca
import datetime
from omegaconf import OmegaConf
import time as t

def submit(cfg, bid=10):
    cluster_repo_path = "/home/rdanecek/workspace/repos/gdl"
    submission_dir_local_mount = "/home/rdanecek/Workspace/mount/scratch/rdanecek/emoca/submission"
    submission_dir_cluster_side = "/ps/scratch/rdanecek/emoca/submission"
    time = datetime.datetime.now().strftime("%Y_%m_%d_%H-%M-%S")
    submission_folder_name = time + "_" + "submission"
    submission_folder_local = Path(submission_dir_local_mount) / submission_folder_name
    submission_folder_cluster = Path(submission_dir_cluster_side) / submission_folder_name

    local_script_path = Path(train_emodeca.__file__).absolute()
    cluster_script_path = Path(cluster_repo_path) / local_script_path.parents[1].name \
                          / local_script_path.parents[0].name / local_script_path.name

    submission_folder_local.mkdir(parents=True)

    config_file = submission_folder_local / "config.yaml"

    with open(config_file, 'w') as outfile:
        OmegaConf.save(config=cfg, f=outfile)

    # python_bin = 'python'
    python_bin = '/home/rdanecek/anaconda3/envs/<<ENV>>/bin/python'
    username = 'rdanecek'
    gpu_mem_requirement_mb = cfg.learning.gpu_memory_min_gb * 1024
    # gpu_mem_requirement_mb = None
    cpus = cfg.data.num_workers + 2 # 1 for the training script, 1 for wandb or other loggers (and other stuff), the rest of data loading
    # cpus = 2 # 1 for the training script, 1 for wandb or other loggers (and other stuff), the rest of data loading
    gpus = cfg.learning.num_gpus
    num_jobs = 1
    max_time_h = 36
    max_price = 10000
    job_name = "train_deca"
    cuda_capability_requirement = 6
    mem_gb = 16
    args = f"{config_file.name}"

    execute_on_cluster(str(cluster_script_path),
                       args,
                       str(submission_folder_local),
                       str(submission_folder_cluster),
                       str(cluster_repo_path),
                       python_bin=python_bin,
                       username=username,
                       gpu_mem_requirement_mb=gpu_mem_requirement_mb,
                       cpus=cpus,
                       mem_gb=mem_gb,
                       gpus=gpus,
                       num_jobs=num_jobs,
                       bid=bid,
                       max_time_h=max_time_h,
                       max_price=max_price,
                       job_name=job_name,
                       cuda_capability_requirement=cuda_capability_requirement
                       )
    t.sleep(1)


def train_emodeca_on_cluster():
    from hydra.core.global_hydra import GlobalHydra

    conf = "emodeca_coarse_cluster"
    deca_conf = "deca_train_detail_cluster"

    training_modes = [
        # DEFAULT
        [
            [],
            []
        ]
    ]
    fixed_overrides_cfg = []
    fixed_overrides_deca = [
        'model/settings=coarse_train_expdeca',
        'model/paths=desktop',
        'model/flame_tex=bfm_desktop',
        'model.resume_training=True',  # load the original DECA model
        'model.useSeg=rend', 'model.idw=0',
        'learning/batching=single_gpu_coarse',
        # 'learning/batching=single_gpu_detail',
         'model.shape_constrain_type=None',
        'data/datasets=affectnet_cluster',
        'learning.batch_size_test=1'
    ]


    for mode in training_modes:
        conf_overrides = fixed_overrides_cfg.copy()
        deca_overrides = fixed_overrides_deca.copy()
        # if len(fmode[0]) != "":
        conf_overrides += mode[0]
        deca_overrides += mode[1]

        cfg = train_emodeca.configure(
            conf, conf_overrides,
            deca_conf, deca_overrides
        )

        GlobalHydra.instance().clear()

        submit(cfg)


if __name__ == "__main__":
    train_emodeca_on_cluster()
