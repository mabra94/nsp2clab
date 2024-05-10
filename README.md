### General Description

Inspired through the work done [here](https://github.com/srl-labs/clab-io-draw) I wanted to create something similar based on an actual Topology that was discovered by an NMS. In this case the NMS is the Nokia Network Services Platform (NSP).

So the main goal is the ability to create drawio diagrams from actual live network data. 

This script allows the export of L2 Topology information in RFC8944 compliant format from an active NSP instance:
- it connects to an NSP server using provided information such as credentials, server IP, proxy address
- it pulls the L2 topology information
- it revokes the authentication token again

Furthermore the retrieved data is transformed into an [containerlab](https://containerlab.dev/) yaml format which can be used to feed into the "clab-io-draw" script to create drawio diagrams. 

### Usage Example

#### nsp2clab

The only mandatory argument that needs to be provided is the NSP Server IP Address (or hostname).

```shell
python3 nsp2clab.py -s [NSP Server IP]
Enter your username: [username]
Enter your password:
```
In that case the script will prompt you for username and password.

Alternatively you can also provide username and password as additional arguments:

```shell
python3 nsp2clab.py -s [NSP Server IP] -u [username] -p [password]
```

There is also the option to provide a proxy server using the "--proxy" flag. The proxy implementation is currently very rudimentary though. 

In addition an output path can be specified. If no ouput path is specified, a file called "data.clab.yaml" is created in the current working directory. 

#### clab2drawio

As mentioned in the beginning, the main driver for this script was the will and interest to generate a drawio diagram based on the actual live network information. 

The script in this repo outputs a containerlab topology compliant .clab.yaml file which can be used in [this](https://github.com/srl-labs/clab-io-draw) script to finally create the drawio diagram.

```shell
python3 clab2drawio.py -i data.clab.yaml --layout horizontal
```

### Known Limitations

- the rendered containerlab yaml files are currently not executable/runnable due to the following constraints:
    - the detailed device information are not collected (e.g. chassis type, OS type and version)
    - virtual SROS devices (vSIMs) that can be run as part of a containerlab topology can not use all possible ports (e.g. we can only use the first breakout port in case we use connector ports) and the script does not handle any port mappings

- proxy implementation is quite limited 