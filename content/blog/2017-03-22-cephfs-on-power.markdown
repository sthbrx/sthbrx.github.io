Title: Evaluating CephFS on Power
Date: 2017-03-22
Authors: Alastair D'Silva
Category: Development
Tags: ceph, raid, storage

## Methodology

To evaluate CephFS, we will create a ppc64le virtual machine, with sufficient
space to compile the software, as well as 3 sparse 1TB disks to create the
object store.

We will then build & install the Ceph packages, after adding the PowerPC
optimisiations to the code. This is done, as ceph-deploy will fetch prebuilt
packages that do not have the performance patches if the packages are not
installed.

Finally, we will use the ceph-deploy to deploy the instance. We will ceph-deploy
via pip, to avoid file conflicts with the packages that we built.

For more information on what each command does, visit the following tutorial,
upon which which this is based: http://palmerville.github.io/2016/04/30/single-node-ceph-install.html

### Virtual Machine Config

Create a virtual machine with at least the following:
 - 16GB of memory
 - 16 CPUs
 - 64GB disk for the root filesystem
 - 3 x 1TB for the Ceph object store
 - Ubuntu 16.04 default install (only use the 64GB disk, leave the others unpartitioned)

### Initial config
 - Enable ssh
```
    sudo apt install openssh-server
    sudo apt update
    sudo apt upgrade
    sudo reboot
```
 - Install build tools
```
    sudo apt install git debhelper
```

### Build Ceph
 - Clone the Ceph repo by following the instructions here: http://docs.ceph.com/docs/master/install/clone-source/
```
    mkdir $HOME/src
    cd $HOME/src
    git clone --recursive https://github.com/ceph/ceph.git  # This may take a while
    cd ceph
    git checkout master
    git submodule update --force --init --recursive
```
 - Cherry-pick the Power performance patches:
```
    git remote add kestrels https://github.com/kestrels/ceph.git
    git fetch --all
    git cherry-pick 59bed55a676ebbe3ad97d8ec005c2088553e4e11
```
 - Install prerequisites
```
    ./install-deps.sh
    sudo apt install python-requests python-flask resource-agents curl python-cherrypy python3-pip python-django python-dateutil python-djangorestframework
    sudo pip3 install ceph-deploy
```
 - Build the packages as per the instructions: http://docs.ceph.com/docs/master/install/build-ceph/
```
    cd $HOME/src/ceph
    sudo dpkg-buildpackage -J$(nproc) # This will take a couple of hours (16 cpus)
```
 - Install the packages (note that python3-ceph-argparse will fail, but is safe to ignore)
```
    cd $HOME/src
    sudo dpkg -i *.deb
```

### Create the ceph-deploy user
```
    sudo adduser ceph-deploy
    echo "ceph-deploy ALL = (root) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/ceph-deploy
    sudo chmod 0440 /etc/sudoers.d/ceph-deploy
```

### Configure the ceph-deploy user environment
```
    su - ceph-deploy
    ssh-keygen
    node=`hostname`
    ssh-copy-id ceph-deploy@$node
    mkdir $HOME/ceph-cluster
    cd $HOME/ceph-cluster
    ceph-deploy new $node # If this fails, remove the bogus 127.0.1.1 entry from /etc/hosts
    echo 'osd pool default size = 2' >> ceph.conf
    echo 'osd crush chooseleaf type = 0' >> ceph.conf
```

### Complete the Ceph deployment
```
    ceph-deploy install $node
    ceph-deploy mon create-initial
    drives="vda vdb vdc"  # the 1TB drives - check that these are correct for your system
    for drive in $drives; do ceph-deploy disk zap $node:$drive; ceph-deploy osd prepare $node:$drive; done
    for drive in $drives; do ceph-deploy osd activate $node:/dev/${drive}1; done
    ceph-deploy admin $node
    sudo chmod +r /etc/ceph/ceph.client.admin.keyring
    ceph -s # Check the state of the cluster
```

### Configure CephFS
```
    ceph-deploy mds create $node
    ceph osd pool create cephfs_data 128
    ceph osd pool create cephfs_metadata 128
    ceph fs new cephfs cephfs_metadata cephfs_data
    sudo systemctl status ceph\*.service ceph\*.target # Ensure the ceph-osd, ceph-mon & ceph-mds daemons are running
    sudo mkdir /mnt/cephfs
    key=`grep key ~/ceph-cluster/ceph.client.admin.keyring | cut -d ' ' -f 3`
    sudo mount -t ceph $node:6789:/ /mnt/cephfs -o name=admin,secret=$key
```


## References

1. http://docs.ceph.com/docs/master/install/clone-source/
2. http://docs.ceph.com/docs/master/install/build-ceph/
3. http://palmerville.github.io/2016/04/30/single-node-ceph-install.html