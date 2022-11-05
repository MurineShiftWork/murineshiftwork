# Notes


### rpi re-install
```shell
  123  rm -rf .conda
  124  sudo chmod -R 777 miniconda3/
  125  conda create -y -n py36 python=3.6 numpy pandas pyzmq

  126  nano .bashrc # source activate py36

  128  pip install git+https://github.com/larsrollik/rpi_camera_colony#egg=rpi_camera_colony[rpi]
  129  rcc_acquisition -a -s
  130  sudo chmod -R 777 data/
  131  rcc_acquisition -a -s
```

sudo rm -rf .conda && sudo chmod -R 777 miniconda3/ && conda create -y -n py36 python=3.6 numpy pandas pyzmq
