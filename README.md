# System Dependencies

## For Debian-based Linux distros
```bash
sudo apt update
sudo apt upgrade
sudo apt install python3 git build-essential
```

## For Arch-based Linux distros
```bash
sudo pacman -Syu base-devel
```

## For Windows Users
1. Install [Debian WSL](https://docs.microsoft.com/en-us/windows/wsl/install-win10#manual-installation-steps)
2. Install dependencies as listed for Debian-based distros above.
3. Send me message on discord if that doesn't work lol.

## For MacOS Users
I think you have to buy a DLC, I dunno lol...

# Installation 

```bash
git clone https://github.com/stivenroytman/evennia-prototyping
cd evennia-prototyping 
make install
```

# Usage

```bash
# Before you start doing anything
source env/bin/activate
 
# Generating a game from repository root
evennia --init gamename # gamename can be changed to anything you like

# Starting a server for your game
cd gamename
evennia start
```
After starting your server, you can visit it in your browser at the following address:
http://localhost:4001 # this is running on your computer

After signing up and/or logging in, you will be presented with the option to join the game on the header menu.

Doing so will connect you to the game, where you can interact with and build a game world.

