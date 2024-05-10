from base64 import b64encode, b64decode
from collections import defaultdict
import os
import requests
import json
import sys
import yaml
import argparse, getpass

def get_username(prompt="Enter your username: "):
    """
    Get the username from the user.

    :param str prompt: The prompt to display to the user.
    :return: The username entered by the user.
    :rtype: str
    """
    print(prompt, end='', flush=True)
    username = input()
    return username

def getBasicAuthentication(username, password):
    """
    Abstract away the encoding and usage of environment
    variables to create the Basic authentication string
    used towards NSP to get a Bearer token.

    :param str username: The username to use for Basic authentication.
    :param str password: The password to use for Basic authentication.
    :return: The Basic authentication string.
    :rtype: str
    """
    return b64encode(
        bytes(
            username + ":" + password, "utf-8"
        )
    ).decode("utf-8")

def getToken(nsp_server, username, password, proxies):
    """
    Use Basic Authentication to get a Bearer token for use in communication
    with NSP.

    :param str nsp_server: The IP address of the NSP, in string form.
    :param str username: The username to use for Basic authentication.
    :param str password: The password to use for Basic authentication.
    :param dict of (str,str) proxies: http_proxy with authentication as
        required (or not required)
    :return: A dictionary containing the access token and other information.
    :rtype: dict
    """
    url = "https://" + nsp_server + "/rest-gateway/rest/api/v1/auth/token"
    body = json.dumps({"grant_type": "client_credentials"})
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {getBasicAuthentication(username, password)}",
    }

    token = requests.post(
        url,
        headers=headers,
        data=body,
        verify=False,
        proxies=proxies,
    )
    # could do something with refresh_token and expires_in values if
    # this will end up being used for a longer-running process but in
    # this case that is unnecessary
    return token.json()


def revokeToken(nsp_server, username, password, token, proxies):
    """
    After completing tasks and work, the token acquired in getToken should be
    cleaned up to not overload the NSP with open/active sessions. The Bearer
    token can be passed to this function to invalidate it on the NSP and clean
    up the open session.

    :param str nsp_server: The IP address of the NSP, in string form.
    :param str username: The username to use for Basic authentication.
    :param str password: The password to use for Basic authentication.
    :param str token: The token to revoke.
    :param dict of (str,str) proxies: https_proxy with authentication as
        required (or not required)
    :return: None
    """
    # revoke token after task is done for sanity reasons
    # nsp has max amount of auth clients allowed
    # makes sense to revoke afterwards

    url = "https://" + nsp_server + "/rest-gateway/rest/api/v1/auth/revocation"
    body = "token=" + token + "&token_type_hint=token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {getBasicAuthentication(username, password)}",
    }
    revToken = requests.post(
        url,
        headers=headers,
        data=body,
        verify=False,
        proxies=proxies,
    )

    # TODO error handling
    if revToken.status_code == 200:
        print("Succesfully revoked token.")
    else:
        print("Error after token revocation attempt.")

def retrieveNspL2IetfTopo(nsp_server, proxies, headers):
    """
    Retrieve the IETF L2 Topology from NSP.

    :param str nsp_server: The IP address of the NSP, in string form.
    :param dict of (str,str) proxies: http_proxy with authentication as
        required (or not required)
    :param dict of (str,str) headers: headers that specify application/json
        and Bearer authentication with the token.
    :return: The IETF L2 Topology data.
    :rtype: dict
    """
    url = (
        "https://"
        + nsp_server
        + "/restconf/data/ietf-network:networks/network=L2Topology"
    )
    l2topo = requests.get(
        url,
        headers=headers,
        verify=False,
        proxies=proxies,
    )

    return l2topo.json()

def generate_topology(json_data):
    """
    Generate a containerlab topology dictionary from the IETF L2 Topology data.

    :param dict json_data: The IETF L2 Topology data.
    :return: The containerlab topology dictionary.
    :rtype: dict
    """
    topology = {"topology": {"nodes": {}, "links": []}}

    # Iterate over nodes
    for node in json_data["ietf-network:network"][0]["node"]:
        node_id = node["node-id"]
        node_name = node["ietf-l2-topology:l2-node-attributes"]["name"]
        node_mgmt_ip = node["ietf-l2-topology:l2-node-attributes"]["management-address"][0]
        topology["topology"]["nodes"][node_name] = {"kind": "nokia-sros", "image": "containerlab/vr-sros", "mgmt-ipv4": node_mgmt_ip}

    # Iterate over links
    for link in json_data["ietf-network:network"][0]["ietf-network-topology:link"]:
        src_endpoint = link["ietf-l2-topology:l2-link-attributes"]["name"].split('--')[0]
        dst_endpoint = link["ietf-l2-topology:l2-link-attributes"]["name"].split('--')[-1]
        topology["topology"]["links"].append({"endpoints": [f"{src_endpoint}", f"{dst_endpoint}"]})

    return topology

def main(server, username, password, output, proxy):
    """
    Generate a containerlab topology file from the IETF L2 Topology data.

    :param str server: The IP Address or Hostname of the NSP Server
    :param str username: The username to use for Basic authentication.
    :param str password: The password to use for Basic authentication.
    :param str output: The output file path for the generated clab topo file.
    :param str proxy: The proxy to use for requests to the NSP.
    """
    # Silence annoying warnings
    from urllib3 import exceptions, disable_warnings        # noqa: E501 pylint: disable=import-outside-toplevel
    disable_warnings(exceptions.InsecureRequestWarning)

    proxies = {}

    if proxy:
        proxies = {
            "https": "http://"+proxy,
            }
        
    if not username:
        username = get_username()

    if not password:
        password = getpass.getpass("Enter your password: ")

    try:
        token = getToken(server, username, password, proxies)
        token = token["access_token"]
    except requests.exceptions.ProxyError as error:
        print(
            "Failed to authenticate on proxy. Exiting as that means all"
            " future comms to the proxy will fail as well.\n"
            "Are the credentials set correctly in your environment?"
            f" Exact error:\n\n{error}\nProxies:\t{proxies}\n"
            f"Auth username:\t{os.environ['PROXY_USER']}"
        )
        sys.exit(0)
    except KeyError as error:
        print(
            "It seems that a KeyError occurred while trying to get a Bearer"
            "token using Basic Auth against NSP\nThis has been the case when"
            "an incorrect password is set in your environment."
            f" Please verify!\n\n{error}--{token}"
        )
        sys.exit(0)

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + token,
    }

    l2topo = retrieveNspL2IetfTopo(
        os.environ["NSP_SERVER"],
        proxies,
        headers
    )
    
    #revoking token again
    revokeToken(server, username, password, token, proxies)

    topology = generate_topology(l2topo)

    if not output:
        output = os.path.join(os.getcwd(), 'data.clab.yaml')

    # Writing data into the YAML file
    with open(output, 'w') as file:
        yaml.dump(dict(topology), file)

    #print(yaml.dump(dict(topology), default_flow_style=False))

def parse_arguments():
    parser = argparse.ArgumentParser(description='Generate a topology file from a NSPs IETF L2 Topology compliant topology information')
    parser.add_argument('-s', '--server', required=True, help='The IP Address or Hostname of the NSP Server')
    parser.add_argument('-u', '--username', required=False, help='Username used to access NSP ')
    parser.add_argument('-p', '--password', required=False, help='Password for the specific user to use for NSP access')
    parser.add_argument('-o', '--output', required=False,
                        help='The output file path for the generated clab topo file. If no output is provided a file called data.clab.yaml is wrriten into current working path')
    parser.add_argument('--proxy', required=False, help='You can specify a proxy in case you need one to access your NSP Server')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()

    main(args.server, args.username, args.password, args.output, args.proxy)
