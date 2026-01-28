"""JIRA text parser for extracting requirements."""

import re
from typing import Dict, List, Any


def parse_jira_text(text: str) -> Dict[str, Any]:
    """
    Parse JIRA requirement text and extract structured information.
    
    Args:
        text: Raw JIRA ticket text (copy/pasted)
        
    Returns:
        Dictionary with extracted requirements including:
        - actions: List of identified actions to perform
        - parameters: Extracted parameters (hostnames, IPs, WWPNs, etc.)
        - keywords: Identified keywords for rule matching
    """
    requirements = {
        "raw_text": text,
        "actions": [],
        "parameters": {},
        "keywords": [],
        "entities": {}
    }
    
    # Normalize text
    text_lower = text.lower()
    
    # Extract keywords for rule matching
    keywords = extract_keywords(text_lower)
    requirements["keywords"] = keywords
    
    # Extract actions from text
    actions = extract_actions(text_lower)
    requirements["actions"] = actions
    
    # Extract parameters (WWPNs, IPs, hostnames, VSAN IDs, etc.)
    parameters = extract_parameters(text)
    requirements["parameters"] = parameters
    
    # Extract named entities
    entities = extract_entities(text)
    requirements["entities"] = entities
    
    return requirements


def extract_keywords(text: str) -> List[str]:
    """Extract relevant keywords from text for rule matching."""
    # Define keyword patterns to look for
    keyword_patterns = [
        # MDS/SAN operations
        r"\b(add|create|provision|configure)\s+(host|server|zone|vsan|vlan)\b",
        r"\b(zone|zoning)\b",
        r"\b(san|mds|fabric)\b",
        r"\b(device\s*alias|devicealias)\b",
        r"\b(zoneset)\b",
        r"\b(vsan|vlan)\b",
        r"\b(fcoe)\b",
        
        # Compute operations
        r"\b(toggle|turn\s*on|turn\s*off)\s*(led|locator)\b",
        r"\b(locator\s*led)\b",
        r"\b(server|compute|blade)\b",
        r"\b(inventory|list)\b",
        r"\b(power\s*(on|off|cycle))\b",
        
        # Configuration operations
        r"\b(save|persist|copy)\s*(config|configuration)\b",
        r"\b(running|startup)\s*config\b",
        
        # General actions
        r"\b(add|create|delete|remove|update|modify)\b",
        r"\b(enable|disable)\b",
        r"\b(activate|deactivate)\b",
    ]
    
    keywords = []
    for pattern in keyword_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                keywords.extend([m for m in match if m])
            else:
                keywords.append(match)
    
    # Deduplicate while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        kw_lower = kw.lower().strip()
        if kw_lower and kw_lower not in seen:
            seen.add(kw_lower)
            unique_keywords.append(kw_lower)
    
    return unique_keywords


def extract_actions(text: str) -> List[Dict[str, str]]:
    """Extract action items from the text."""
    actions = []
    
    # Action patterns with their types
    action_patterns = [
        (r"add\s+(?:new\s+)?host\s+(?:to\s+)?(?:san|zone)", "add_host_to_san"),
        (r"create\s+(?:new\s+)?zone", "create_zone"),
        (r"add\s+(?:to\s+)?zoneset", "add_to_zoneset"),
        (r"create\s+vlan", "create_vlan"),
        (r"provision\s+(?:tenant\s+)?vlan", "provision_vlan"),
        (r"toggle\s+(?:locator\s+)?led", "toggle_led"),
        (r"turn\s+(?:on|off)\s+(?:locator\s+)?led", "toggle_led"),
        (r"save\s+config(?:uration)?", "save_config"),
        (r"copy\s+running.*startup", "save_config"),
        (r"get\s+(?:server\s+)?inventory", "get_inventory"),
        (r"list\s+servers?", "get_inventory"),
        (r"add\s+device\s*alias", "add_device_alias"),
        (r"activate\s+zoneset", "activate_zoneset"),
    ]
    
    for pattern, action_type in action_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            actions.append({
                "type": action_type,
                "pattern_matched": pattern
            })
    
    return actions


def extract_parameters(text: str) -> Dict[str, Any]:
    """Extract parameters like WWPNs, IPs, hostnames, VSAN IDs from text."""
    parameters = {}
    
    # WWPN pattern (xx:xx:xx:xx:xx:xx:xx:xx)
    wwpn_pattern = r"\b([0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})\b"
    wwpns = re.findall(wwpn_pattern, text)
    if wwpns:
        parameters["wwpns"] = wwpns
    
    # IP address pattern
    ip_pattern = r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b"
    ips = re.findall(ip_pattern, text)
    if ips:
        parameters["ip_addresses"] = ips
    
    # VSAN ID pattern (vsan followed by number)
    vsan_pattern = r"\bvsan\s*(?:id\s*)?(\d+)\b"
    vsans = re.findall(vsan_pattern, text, re.IGNORECASE)
    if vsans:
        parameters["vsan_ids"] = [int(v) for v in vsans]
    
    # VLAN ID pattern
    vlan_pattern = r"\bvlan\s*(?:id\s*)?(\d+)\b"
    vlans = re.findall(vlan_pattern, text, re.IGNORECASE)
    if vlans:
        parameters["vlan_ids"] = [int(v) for v in vlans]
    
    # Zone name pattern
    zone_pattern = r"\bzone\s*(?:name\s*)?[:\s]+([a-zA-Z0-9_-]+)\b"
    zones = re.findall(zone_pattern, text, re.IGNORECASE)
    if zones:
        parameters["zone_names"] = zones
    
    # Hostname pattern (generic)
    hostname_pattern = r"\b(?:host(?:name)?|server)\s*[:\s]+([a-zA-Z0-9_.-]+)\b"
    hostnames = re.findall(hostname_pattern, text, re.IGNORECASE)
    if hostnames:
        parameters["hostnames"] = hostnames
    
    # Fabric A/B pattern
    fabric_pattern = r"\bfabric\s*([AB])\b"
    fabrics = re.findall(fabric_pattern, text, re.IGNORECASE)
    if fabrics:
        parameters["fabrics"] = [f.upper() for f in fabrics]
    
    return parameters


def extract_entities(text: str) -> Dict[str, List[str]]:
    """Extract named entities from text."""
    entities = {}
    
    # MDS switch references
    mds_pattern = r"\b(mds[-_\s]?\d+[a-zA-Z0-9_-]*)\b"
    mds_switches = re.findall(mds_pattern, text, re.IGNORECASE)
    if mds_switches:
        entities["mds_switches"] = mds_switches
    
    # Server references
    server_pattern = r"\b((?:ucs|hx|esxi|vmware)[-_\s]?[a-zA-Z0-9_-]+)\b"
    servers = re.findall(server_pattern, text, re.IGNORECASE)
    if servers:
        entities["servers"] = servers
    
    # Storage array references
    storage_pattern = r"\b((?:netapp|pure|nimble|unity|powerstore)[-_\s]?[a-zA-Z0-9_-]*)\b"
    storage = re.findall(storage_pattern, text, re.IGNORECASE)
    if storage:
        entities["storage_arrays"] = storage
    
    return entities
