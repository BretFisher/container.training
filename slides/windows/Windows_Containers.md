class: title

# Windows Containers

![Container with Windows](images/windows-containers.jpg)

---

## Objectives

At the end of this section, you will be able to:

* Understand Windows Container vs. Linux Container.

* Features of Docker for Windows for choosing architecture.

* Run other container architectures via QEMU emulation.

---

## Are Containers *just* for Linux?

Remember that a container must run on the kernel of the OS it's on

  - This is both a benefit and a limitation. 
  
  - Since 2013 Docker launch, many OS's have added support for the Docker runtime.

  - We can now run more than "amd64/linux": including Windows, ARM, i386, IBM mainframes, and more, but no macOS or iOS yet :/

--

  - Docker Desktop (macOS/Win) has a emulator too for ARM/PPC and others
  
  - Later, try running a [Raspberry Pi (ARM) or PPC container](https://docs.docker.com/docker-for-mac/multi-arch/)

---

## History of Windows Containers

- Early 2016, Windows 10 gained support for running Windows binaries in containers.

  - These are known as "Windows Containers"
  - These must run in Hyper-V mini-VM's with a Server kernel 
  - "Core" and "Nano" Server OS options
  - It Expects Docker for Windows to be installed for full features

--

- Late 2016, Windows Server 2016 ships with native Docker support

  - Installed via PowerShell, doesn't need Docker for Windows
  - Can run native (without VM), or with [Hyper-V Isolation](https://docs.microsoft.com/en-us/virtualization/windowscontainers/manage-containers/hyperv-container)

---

## Windows Containers Cont.

Windows is largely playing catch up with Linux but moving fast!

You can now do things on Windows you *can't* do on Linux:

  - LCOW: "Linux Containers on Windows" came with the ([Fall 2017 Creators Update](https://blog.docker.com/2018/02/docker-for-windows-18-02-with-windows-10-fall-creators-update/))
  - Run Linux and Windows containers side-by-side on Win10
  - No longer required to switch to "Linux Containers"

--

Docker for Windows Users, Start Your Engines:

  ```bash
    docker run --rm -it microsoft/nanoserver powershell
  ```

--

Doh! We need to switch to Windows Containers mode

---

## Run Both Windows and Linux containers

- Run a Nano Windows Server (minimal cli-only Win Svr)

  ```bash
  docker run --rm -it microsoft/nanoserver powershell
  Get-Process
  exit
  ```

- Run a Busybox Linux in LCOW


  ```bash
  docker run --rm --platform linux busybox echo hello
  ```

(notice neither of these show up in Hyper-V but they are there, hidden nano and "LinuxKit" VM's)

---

## Other Windows Container options

Most "official" Docker images don't run on Windows yet

Places to Look:
  - Hub Official: https://hub.docker.com/u/winamd64/ 
  - Microsoft: https://hub.docker.com/r/microsoft/

---

## SQL Server? Choice of Linux or Windows

Microsoft [SQL Server for Linux 2017](https://hub.docker.com/r/microsoft/mssql-server-linux/)

Microsoft [SQL Server Express 2017](https://hub.docker.com/r/microsoft/mssql-server-windows-express/)

---

## Windows Tools and Tips

- PowerShell [Tab Completion: DockerCompletion](https://github.com/matt9ucci/DockerCompletion)
- Best Shell GUI: [Cmder.net](http://cmder.net/)
- Best Blog and How-To's, Dockers DevRel [Elton Stoneman, Microsoft MVP](https://blog.sixeyed.com/)
