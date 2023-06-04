from report import Report, BotReactMessage, State
from datetime import datetime
from enum import Enum, auto
import discord
from bot import money_message, impersonating, harrassment, threat, spam

user_false_reports = {}
manual_check_queue = []

HIGHEST_PRI = 1
HIGH_PRI = 2
MED_PRI = 3
LOW_PRI = 4

# possible actions: NO_ACTION, MANUAL, BAN, SUSPEND


def new_report(completed_report, user_being_reported, user_making_report, reports_about_user):
    is_abuse = False
    #if some_condition:  # to do - send this condition from bot.py
    #    is_abuse = True

    # Check abuse type
    reported_issues = completed_report.get_reported_issues()
    decisions = []

    if Report.HARASSMENT in reported_issues:
        decisions.append(harassment_report(user_being_reported, reports_about_user))
    elif Report.SPAM in reported_issues:
        decisions.append(spam_report(reports_about_user[user_being_reported]))
    elif  Report.THREAT in reported_issues[0]:
        decisions.append(threat_report(completed_report))
    elif Report.FRAUD in reported_issues[0]:
        decisions.append(fraud_report(completed_report))
    else:  # Other
        decisions.append(other_report(completed_report))

    # pick most important decision:
    final_decision, final_message, final_pri = "NO_ACTION", "", LOW_PRI
    for decision in decisions:
        d, m, p = decision
        if d == "BAN" and final_decision != "BAN":
             d, m, p = final_decision, final_message, final_pri
        elif d == "SUSPEND" and (final_decision == "NO_ACTION" or final_decision == "MANUAL"):
             d, m, p = final_decision, final_message, final_pri
        elif d == "MANUAL" and final_decision == "MANUAL":
             d, m, p = final_decision, final_message, final_pri
        if d == final_decision and p < final_pri:
             d, m, p = final_decision, final_message, final_pri

    return final_decision


def harassment_report(completed_report, list_of_reports_against_user):
    is_harrassment = spam(completed_report.get_reported_message())

    harrassment_count = 0
    for report in list_of_reports_against_user:
        if Report.HARASSMENT in report.reported_issues:
            harrassment_count += 1

    if is_harrassment and harrassment_count < 3:
        'SUSPEND', "Your message was marked as harmful, you have been suspended " \
                          "for 15 days. Please contact us if you think we made a mistake.", MED_PRI
    elif harrassment_count >= 3 and is_harrassment:  # many reports of harassment
        return 'BAN', "Your account has been banned due to too many harmful messages.", MED_PRI
    elif harrassment_count > 5:  # many reports of harassment
        return 'SUSPEND', "You have been suspended for 15 days due to harmful messages. Please contact us if you think we made a mistake.", MED_PRI
    else:
        return  "MANUAL", "", MED_PRI


def spam_report(completed_report, list_of_reports_against_user):
    spam_count = 0
    is_spam = spam(completed_report.get_reported_message())
    for report in list_of_reports_against_user:
        if  Report.SPAM in report.reported_issues[0]:
            spam_count += 1

    if is_spam and spam_count >= 3:  # user has been reported many times for spam
        return 'BAN', "Your account has been banned due to too many spam messages.", MED_PRI
    elif is_spam and spam_count < 3:
        return 'SUSPEND', "Your account has been suspended due to reports of spam messages. ", MED_PRI
    else:
        return 'NO ACTION', ": We did not find this message to be abusive. " \
                          "Please contact us if you think we made a mistake.", LOW_PRI


def threat_report(completed_report):
    is_threat = threat(completed_report.get_reported_message)
    if is_threat:
        return 'BAN', "Your account has been banned due to harmful messages.", HIGH_PRI
    return 'MANUAL', "", HIGHEST_PRI


def fraud_report(completed_report):
    reported_issues = completed_report.get_reported_issues()

    if Report.REQUESTED_MONEY in reported_issues:
        # if Report.OBTAINED_MONEY in reported_issues:  # requested and obtained money
        #     return 'MANUAL', "Your account is under review due to reports of fraud.", HIGH_PRI
        # else:  # requested but did not obtain money
        if money_message(completed_report.get_reported_message()) == "yes":
            return 'BAN', "Your account has been banned due to reports of monetary fraud.", HIGH_PRI
        else:
            return 'MANUAL', "Your account is under review due to reports of fraud", HIGHEST_PRI
    elif Report.IMPERSONATION in reported_issues:
        if impersonating(completed_report.get_reported_message()) == "yes":
            return 'BAN', "Your account has been banned due to reports of impersonation.", HIGH_PRI
        else:
            return 'MANUAL', "Your account is under review due to reports of fraud.", MED_PRI

    elif Report.FALSE_INFO in reported_issues:
        return 'MANUAL', "Your account is under review due to reports of fraud.", MED_PRI
    else:
        return other_report(completed_report)


def other_report(completed_report):
    response = "Your report has been placed in our queue for manual moderation."
    return 'MANUAL', response, LOW_PRI