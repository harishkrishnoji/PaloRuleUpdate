# pylint: disable=R0916
"""Palo Alto Rules - Log Profile Update."""
import sys
import os
import panos
from panos import panorama
from helper_fts.email import send_email
from helper_fts.logger import get_logger

# Global Variables and parameters


HOSTNAME = os.environ.get("RD_OPTION_PAN_NAME")
API_KEY = os.environ.get("RD_OPTION_APIKEY")
DGROUP_LST = os.environ.get("RD_OPTION_DGROUP").split(",")
RULE_UPDATE = "YES" in os.environ.get("RD_OPTION_RUPDATE")
pan = panorama.Panorama(HOSTNAME, api_key=API_KEY, port=443)
emailR = []
logger = get_logger("PaloAlto_Log_Profile_Update", **{"stream": sys.stdout})


def get_rulebase(device):
    """This function will create configuration tree and retrun security rules for respective Device group.

    Args:
        device (str): Device Group name.
    """
    device_group = panos.panorama.DeviceGroup(device)
    pre_rulebase = panos.policies.PreRulebase()
    # post_rulebase = panos.policies.PostRulebase()
    # device_group.extend([pre_rulebase, post_rulebase])
    device_group.extend([pre_rulebase])
    pan.add(device_group)
    security_rules = panos.policies.SecurityRule.refreshall(pre_rulebase)
    # security_rules.extend(panos.policies.SecurityRule.refreshall(post_rulebase))
    return security_rules


def update_rule(rule):
    """This function will update group and log settings to default.

    Args:
        rule (class): Class Rule.
    """
    if RULE_UPDATE:
        logger.info("Updated Rule: %s", rule.name)
        rule.group = ["default"]
        rule.log_setting = "default"
        rule.log_start = False
        rule.log_end = True


def apply_rule(sec_rules):
    """This function will commit changes to Panorama.

    Args:
        sec_rules (Class): Class Rulebase.
    """
    if RULE_UPDATE:
        sec_rules[0].apply_similar()
        logger.info("Updated Rules were commited to Panaram")


def display_results(sec_rules):
    """This function prase each rule and check if log/profile is set to default.

    Args:
        sec_rules (Class): Class Rulebase.
    """
    for rule in sec_rules:
        if (
            (not rule.log_setting and (not rule.tag or "No-Log" not in rule.tag))
            or (not rule.group)
            or (not isinstance(rule.group, list))
            or (rule.log_setting != "default" and (not rule.tag or "No-Log" not in rule.tag))
            or (
                rule.group[0] != "default"
                and rule.group[0] != "scanner"
                and (not rule.tag or "Blacklists" not in rule.tag)
            )
        ) and (rule.action == "allow"):

            lnu = 4 if not rule.log_setting else len(rule.log_setting)
            gnu = 2 if not rule.group else len(str(rule.group))
            emailR.append(f"{rule.log_setting}{' '*(15-lnu)}{rule.group}{' '*(20-gnu)}{rule.name}")
            update_rule(rule)
    apply_rule(sec_rules)


if __name__ == "__main__":
    logger.info("Policy Update: %s", RULE_UPDATE)
    logger.info("Device Group list to Prase: %s", DGROUP_LST)
    logger.info("Gathering list of Device Group...")
    emailR.append("List of PaloAlto rules which does not have LogSetting, Group, LogStart, and LogEnd set properly")
    emailR.append(f"{'='*100}")
    emailR.append(f"Update profile is set to : {os.environ.get('RD_OPTION_RUPDATE')}")
    emailR.append(f"{'='*60}")
    emailR.append(f"LogSetting{' '*(15-10)}Group{' '*(20-5)}RuleName")
    for dev in list(panos.panorama.PanoramaDeviceGroupHierarchy(pan).fetch()):
        if dev in DGROUP_LST or "All" in DGROUP_LST:
            emailR.append(f"{'='*60} {dev}")
            logger.info("Gathering Security Rulebase for DeviceGroup: %s...", dev)
            secrules = get_rulebase(dev)
            display_results(secrules)

    msg = {}
    msg["to"] = "Rodrigo.Miranda@fiserv.com, mohana.ramaswamy@fiserv.com, mike.mahon@fiserv.com"
    msg["cc"] = "georgette.ewan@fiserv.com, harish.krishnoji@fiserv.com, Andy.Clark@fiserv.com"
    msg["body"] = emailR
    logger.info("Sending Email Notification...")
    send_email(**msg)
    logger.info("DONE")
