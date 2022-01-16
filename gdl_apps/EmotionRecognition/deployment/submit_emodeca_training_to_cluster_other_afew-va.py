from gdl.utils.condor import execute_on_cluster
from pathlib import Path
import gdl_apps.EmotionRecognition.training.train_emodeca as script
# import gdl_apps.EmotionRecognition.training.train_emo3ddfa as script
import datetime
from omegaconf import OmegaConf
import time as t
import random

project_name = "EmoDECA_Afew-VA"


def submit(cfg, bid=10):
    cluster_repo_path = "/home/rdanecek/workspace/repos/gdl"
    # submission_dir_local_mount = "/home/rdanecek/Workspace/mount/scratch/rdanecek/emoca/submission"
    # submission_dir_local_mount = "/ps/scratch/rdanecek/emoca/submission"
    # submission_dir_cluster_side = "/ps/scratch/rdanecek/emoca/submission"

    submission_dir_local_mount = "/is/cluster/work/rdanecek/emoca/submission"
    submission_dir_cluster_side = "/is/cluster/work/rdanecek/emoca/submission"

    time = datetime.datetime.now().strftime("%Y_%m_%d_%H-%M-%S")
    submission_folder_name = time + "_" + str(hash(random.randint(0, 100000))) + "_" + "submission"
    submission_folder_local = Path(submission_dir_local_mount) / submission_folder_name
    submission_folder_cluster = Path(submission_dir_cluster_side) / submission_folder_name

    local_script_path = Path(script.__file__).absolute()
    # local_script_path = Path(train_emo3ddfa.__file__).absolute()
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
    # gpu_mem_requirement_mb_max = cfg.learning.gpu_memory_min_gb * 40
    # gpu_mem_requirement_mb = None
    cpus = cfg.data.num_workers + 2 # 1 for the training script, 1 for wandb or other loggers (and other stuff), the rest of data loading
    # cpus = 2 # 1 for the training script, 1 for wandb or other loggers (and other stuff), the rest of data loading
    gpus = cfg.learning.num_gpus
    num_jobs = 1
    max_time_h = 36
    max_price = 10000
    job_name = "train_deca"
    cuda_capability_requirement = 7
    mem_gb = 16
    # mem_gb = 30
    args = f"{config_file.name} {-1} {1} {0} {project_name}"

    execute_on_cluster(str(cluster_script_path),
                       args,
                       str(submission_folder_local),
                       str(submission_folder_cluster),
                       str(cluster_repo_path),
                       python_bin=python_bin,
                       username=username,
                       gpu_mem_requirement_mb=gpu_mem_requirement_mb,
                       # gpu_mem_requirement_mb_max=gpu_mem_requirement_mb_max,
                       cpus=cpus,
                       mem_gb=mem_gb,
                       gpus=gpus,
                       num_jobs=num_jobs,
                       bid=bid,
                       max_concurrent_jobs=30,
                       max_time_h=max_time_h,
                       max_price=max_price,
                       job_name=job_name,
                       cuda_capability_requirement=cuda_capability_requirement,
                       chmod=False,
                       modules_to_load=['cuda/11.4']
                       )
    # t.sleep(2)


def train_emodeca_on_cluster():
    from hydra.core.global_hydra import GlobalHydra


    training_modes = [
        [
            [
                'model.use_identity=true',
                'model.use_expression=true',],
            []
        ],
        [
            [
                'model.use_identity=false',
                'model.use_expression=true',],
            []
        ],
    ]

    # # ## 1) Emo 3DDFA_V2
    emodeca_default = "emo3ddfa_v2"
    emodeca_overrides = [
        # 'model/backbone=3ddfa_v2',
        'model/backbone=3ddfa_v2_resnet',
        'model.mlp_dim=2048',
        'model.predict_expression=false',
        'data/datasets=afew_va',
        'data/augmentations=none',
        'data.num_workers=16',
    ]

    # # ## 2) Deep 3D Face
    # emodeca_default = "deep3dface"
    # emodeca_overrides = [
    #     'model/backbone=deep3dface',
    #     'model.mlp_dim=2048',
    #     'model.predict_expression=false',
    #     'data/datasets=afew_va',
    #     'data/augmentations=none',
    #     # 'data.num_workers=0',
    #     'data.num_workers=16',
    #     # 'learning/logging=none',
    # ]
    #
    # #3) EmoMGCNET
    # emodeca_default = "emomgcnet"
    # emodeca_overrides = [
    #     # 'model.mlp_dim=2048',
    #     'model.predict_expression=false',
    #     'data/datasets=afew_va',
    #     '+data.dataset_type=AfewVaWithMGCNetPredictions',
    #      'learning.gpu_memory_min_gb=12',
    #     'data/augmentations=none',
    #     'data.num_workers=16',
    # ]

    # # 4) EmoExpNET
    # emodeca_default = "emoexpnet"
    # emodeca_overrides = [
    #     # 'model.mlp_dim=2048',
    #     'model.predict_expression=false',
    #     'data/datasets=afew_va',
    #     '+data.dataset_type=AfewVaWithExpNetPredictions',
    #     'learning.gpu_memory_min_gb=12',
    #     'data/augmentations=none',
    #     'data.num_workers=16',
    # ]

    deca_conf = None
    deca_conf_path = None
    fixed_overrides_deca = None
    stage = None

    for mode in training_modes:
        conf_overrides = emodeca_overrides.copy()
        conf_overrides += mode[0]
        if deca_conf_path is None and fixed_overrides_deca is not None:
            deca_overrides = fixed_overrides_deca.copy()
            deca_overrides += mode[1]
        else:
            deca_overrides=None

        cfg = train_emodeca.configure(
            emodeca_default, conf_overrides,
            deca_default=deca_conf, deca_overrides=deca_overrides,
            deca_conf_path=deca_conf_path ,
            deca_stage=stage
        )
        GlobalHydra.instance().clear()

        # sub = False
        sub = True
        if sub:
            submit(cfg)
        else:
            train_emodeca.train_emodeca(cfg, -1,1,0, project_name)


if __name__ == "__main__":
    train_emodeca_on_cluster()
