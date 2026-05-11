# MISC - misc info

Installing docker into WSL
```
# Inside WSL (Ubuntu/Debian-style):
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io
sudo usermod -aG docker $USER
```

Running eval requires the daemon to be up w/ the user in the docker group
```
sudo service docker status # check if up
newgrp docker # apply group to curr shell
docker info # check for no permission denied
docker run --rm hello-world # sanity check
```

Create a empty mini-swe-agent config to use run_agent in rerun
It'll prompt for creation of a default global config on the first run otherwise
```
touch ~/.config/mini-swe-agent/.env
```