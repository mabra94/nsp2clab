### General Description

Inspired through the work done [here](https://github.com/srl-labs/clab-io-draw) I wanted to create something similar based on an actual Topology that was discovered by an NMS. In this case the NMS is the Nokia Network Services Platform (NSP).

So the main goal is the ability to create drawio diagrams from actual live network data. 

This script allows the export of L2 Topology information in RFC8944 compliant format from an active NSP instance:
- it connects to an NSP server using provided information such as credentials, server IP, proxy address
- it pulls the L2 topology information
- it revokes the authentication token again

Furthermore the retrieved data is transformed into an [containerlab](https://containerlab.dev/) yaml format which can be used to feed into the "clab-io-draw" script to create drawio diagrams. 

### Known Limitations

- the rendered containerlab yaml files are currently not executable/runnable due to the following constraints:
    - the detailed device information are not collected (e.g. chassis type, OS type and version)
    - virtual SROS devices (vSIMs) that can be run as part of a containerlab topology can not use all possible ports (e.g. we can only use the first breakout port in case we use connector ports) and the script does not handle any port mappings