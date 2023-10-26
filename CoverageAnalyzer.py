from utils import *
import os
import subprocess

import xmltodict
from pprint import pprint
import matplotlib.pyplot as plt

import requests
import json

import logging
import pickle

from unidiff import PatchSet
import linecache

import pandas as pd


class CoverageAnalyzer:
    def __init__(self, github_token, url, path=None, module_path=None,
                 coverage_tool="jacoco", num_commits=15, start_date="2018-01-01", end_date=None):
        repo_author = url.split("/")[-2]
        repo_name = url.split("/")[-1]

        self.github_token = github_token
        self.url = url
        self.repo_author = repo_author
        self.repo_name = repo_name
        self.path = path
        self.module_path = module_path
        self.coverage_tool = coverage_tool
        self.num_commits = num_commits
        self.start_date = start_date
        self.end_date = end_date

    def new_create_heatmap_data(self, commit_diff_list, line_number_coverage):
        df = pd.DataFrame(columns=["file_name", "file_name_short", "line_number", "count", "coverage"])
        covered_line_numbers, uncovered_line_numbers = line_number_coverage

        heatmap = dict()
        for commit_diff in commit_diff_list:
            for file_diff in commit_diff:
                file_name = file_diff[0]
                # file_name_split = file_name.split("/")
                lines_changed = file_diff[1] + file_diff[2]
                for line_number in lines_changed:
                    if file_name not in heatmap:
                        heatmap[file_name] = dict()
                    if line_number not in heatmap[file_name]:
                        heatmap[file_name][line_number] = 1
                    else:
                        heatmap[file_name][line_number] += 1
        for file_name, lines in heatmap.items():
            file_name_short = file_name.split("/")[-1]
            for line_number in lines:
                if file_name_short in covered_line_numbers and line_number in covered_line_numbers[file_name_short]:
                    new_record = pd.DataFrame([{"file_name": file_name, "file_name_short": file_name_short,
                                                "line_number": line_number, "count": heatmap[file_name][line_number],
                                                "coverage": "covered"}])
                    df = pd.concat([df, new_record], ignore_index=True)
                elif file_name_short in uncovered_line_numbers and line_number in uncovered_line_numbers[
                    file_name_short]:
                    new_record = pd.DataFrame([{"file_name": file_name, "file_name_short": file_name_short,
                                                "line_number": line_number, "count": heatmap[file_name][line_number],
                                                "coverage": "not covered"}])
                    df = pd.concat([df, new_record], ignore_index=True)
                else:
                    new_record = pd.DataFrame([{"file_name": file_name, "file_name_short": file_name_short,
                                                "line_number": line_number, "count": heatmap[file_name][line_number],
                                                "coverage": "neutral"}])
                    df = pd.concat([df, new_record], ignore_index=True)
        return df

    def create_heatmap_data(self, commit_diff_list, line_number_coverage=None):
        if line_number_coverage:
            covered_line_numbers, uncovered_line_numbers = line_number_coverage
        module_heatmap = dict()
        file_heatmap = dict()
        line_heatmap = dict()
        line_covered_heatmap = dict()
        line_uncovered_heatmap = dict()
        highest_line_number_total = 0
        for commit_diff in commit_diff_list:
            for file_diff in commit_diff:
                module_names = list()
                file_name = file_diff[0]
                file_name_split = file_name.split("/")
                for i in range(len(file_name_split) - 1):
                    module_names.append("/".join(file_name_split[:i]))

                if file_diff[1] and file_diff[2]:
                    highest_line_number = max(max(file_diff[1]), max(file_diff[2]))
                elif file_diff[1]:
                    highest_line_number = max(file_diff[1])
                elif file_diff[2]:
                    highest_line_number = max(file_diff[2])
                else:
                    highest_line_number = 0
                if highest_line_number > highest_line_number_total:
                    highest_line_number_total = highest_line_number

                # count file occurrence
                if file_name in file_heatmap:
                    file_heatmap[file_name] += 1
                else:
                    file_heatmap[file_name] = 1
                    # create list of 0's with the length of the highest lines number, which is always in the last element
                    if line_number_coverage:
                        line_covered_heatmap[file_name] = [0] * (highest_line_number_total + 1)
                        line_uncovered_heatmap[file_name] = [0] * (highest_line_number_total + 1)
                    else:
                        line_heatmap[file_name] = [0] * (highest_line_number_total + 1)

                # count module occurrence
                for module_name in module_names:
                    if module_name in module_heatmap:
                        module_heatmap[module_name] += 1
                    else:
                        module_heatmap[module_name] = 1

                # increase list length if it is too short
                if line_number_coverage:
                    if len(line_covered_heatmap[file_name]) < highest_line_number_total + 1:
                        added_length = highest_line_number_total - len(
                            line_covered_heatmap[file_name]) + 1  # potential off-by-one error
                        for file_name, file in line_covered_heatmap.items():
                            file += [0] * added_length
                    if len(line_uncovered_heatmap[file_name]) < highest_line_number_total + 1:
                        added_length = highest_line_number_total - len(
                            line_uncovered_heatmap[file_name]) + 1  # potential off-by-one error
                        for file_name, file in line_uncovered_heatmap.items():
                            file += [0] * added_length
                else:
                    if len(line_heatmap[file_name]) < highest_line_number_total + 1:
                        added_length = highest_line_number_total - len(
                            line_heatmap[file_name]) + 1  # potential off-by-one error
                        for file_name, file in line_heatmap.items():
                            file += [0] * added_length

                # for each line number that either got added or deleted, increase the count
                for line_added in file_diff[1]:
                    if line_number_coverage:
                        if file_name_split[-1] in covered_line_numbers:
                            if line_added in covered_line_numbers[file_name_split[-1]]:
                                line_covered_heatmap[file_name][line_added] += 1
                            if line_added in uncovered_line_numbers[file_name_split[-1]]:
                                line_uncovered_heatmap[file_name][line_added] += 1
                    else:
                        line_heatmap[file_name][line_added] += 1
                        # TODO lines that are neither covered nor uncovered
                for line_deleted in file_diff[2]:
                    if line_number_coverage:
                        if file_name_split[-1] in covered_line_numbers:
                            if line_deleted in covered_line_numbers[file_name_split[-1]]:
                                line_covered_heatmap[file_name][line_deleted] += 1
                            if line_deleted in uncovered_line_numbers[file_name_split[-1]]:
                                line_uncovered_heatmap[file_name][line_deleted] += 1
                    else:
                        line_heatmap[file_name][line_deleted] += 1
        # pad list with 0's for uniform length
        for file_name, file in line_covered_heatmap.items():
            if len(file) < highest_line_number_total + 1:
                file += [0] * (highest_line_number_total - len(file) + 1)
        if line_number_coverage:
            return module_heatmap, file_heatmap, line_covered_heatmap, line_uncovered_heatmap
        else:
            return module_heatmap, file_heatmap, line_heatmap

    def analyze_report(self, report_data):
        """
        analyze_report - Takes Jacoco reports and analyzes line coverage per method.
        :param [{ }, ] report_data:
        :return:
        """
        data = dict()
        line_coverage = dict()
        for i, report in enumerate(report_data):
            if not report:
                continue
            if isinstance(report["report"]["package"], dict):  # true if there is only one class per file
                for java_class in report["report"]["package"]["class"]:
                    for java_method in java_class["method"]:
                        # java_method["counter"][0]["@covered"] is INSTRUCTIONS of one method
                        if not java_class["@name"] in data:
                            data[java_class["@name"]] = dict()
                        if not java_method["@name"] in data[java_class["@name"]]:
                            data[java_class["@name"]][java_method["@name"]] = list()
                        # java_method["counter"][0] means INSTRUCTIONS, 1 means LINES, 2 COMPLEXITY, 3 METHOD, 4 CLASS
                        data[java_class["@name"]][java_method["@name"]].append((
                            int(java_method["counter"][0]["@covered"]), int(java_method["counter"][0]["@missed"])))
            elif isinstance(report["report"]["package"], list):
                for java_file in report["report"]["package"]:
                    for java_class in java_file:
                        pprint(java_file,
                               indent=2)  # TODO: sub-folders result in nested loops, maybe use "sourcefile" instead
                        for java_method in java_class["method"]:
                            # java_method["counter"][0]["@covered"] is INSTRUCTIONS of one method
                            if not java_class["@name"] in data:
                                data[java_class["@name"]] = dict()
                            if not java_method["@name"] in data[java_class["@name"]]:
                                data[java_class["@name"]][java_method["@name"]] = list()
                            # java_method["counter"][0] means INSTRUCTIONS, 1 means LINES, 2 COMPLEXITY, 3 METHOD, 4 CLASS
                            data[java_class["@name"]][java_method["@name"]].append((
                                int(java_method["counter"][0]["@covered"]), int(java_method["counter"][0]["@missed"])))
        for java_class_name, java_class_data in data.items():
            for java_method_name, java_method_data in java_class_data.items():
                if java_method_data[0][1] < java_method_data[-1][1]:
                    logging.info("Coverage of Method %s in Class %s got worse. Coverage: %s", java_method_name,
                                 java_class_name, str(java_method_data[-1]))
                if int(java_method_data[-1][1]) > 0:  # (int(java_method_data[-1][0])):
                    logging.info("Method %s in Class %s has low coverage. Coverage: %s", java_method_name,
                                 java_class_name,
                                 str(java_method_data[-1]))

        # create copy for testing
        with open("report_data", "wb") as file:
            pickle.dump(report_data, file)

    def get_commit_diff(self, commit_old, commit_new):
        """
        get_commit_diff - Takes two commit hashes and gathers their git diff and saves the added and removed line numbers.
        :param commit_old: Commit hash/sha. Branches should work too.
        :param commit_new: Commit hash/sha. Branches should work too.
        :return: [(file_path, added_line_numbers, removed_line_numbers), ]
        """
        headers = {
            'Accept': 'application/vnd.github.diff',
            'Authorization': 'Bearer ' + self.github_token,
        }
        url = "https://api.github.com/repos/" + self.repo_author + "/" + self.repo_name + "/compare/" \
              + commit_old["sha"] + "..." + commit_new["sha"]
        response = requests.get(url, headers=headers)
        logging.info(
            "https://github.com/" + self.repo_author + "/" + self.repo_name + "/compare/" + commit_old["sha"] + "..." +
            commit_new["sha"] + ".diff")
        diff_text = response.text

        patch_set = PatchSet(diff_text)

        commit_diff = []  # list of changes
        # [(file_name, [row_number_of_deleted_line],
        # [row_number_of_added_lines]), ... ]

        for patched_file in patch_set:
            file_path = patched_file.path  # file name
            ad_line_no = [line.target_line_no
                          for hunk in patched_file for line in hunk
                          if line.is_added and
                          line.value.strip() != '']  # the row number of deleted lines
            del_line_no = [line.source_line_no for hunk in patched_file
                           for line in hunk if line.is_removed and
                           line.value.strip() != '']  # the row number of added liens
            commit_diff.append((file_path, ad_line_no, del_line_no))
        return commit_diff

    def get_commits(self):
        """
        get_commits - Collects a certain amount of commit information (hash, date) from github.com/repo_author/repo_name.
            Chosen commits are evenly distributed by commit number, not time.
            Can specify number of commits, start and end date.
        :param str repo_author: Author of repository taken from git_url.
        :param str repo_name: Name of the repository taken from git_url.
        :param int num_commits: Optional: Number of evenly distributed commits you want to analyze.
        :param str start_date: Optional:Date at which to start analyzing commits in the format YYYY-MM-DD.
        :param str end_date: Optional: Date at which to end analyzing commits in the format YYYY-MM-DD.
        :return:
        """
        headers = {
            'Accept': 'application/vnd.github+json',
            'Authorization': 'Bearer ' + self.github_token,
        }
        url = "https://api.github.com/repos/" + self.repo_author + "/" + self.repo_name + \
              "/commits?per_page=1"
        if self.start_date:
            url += "&since" + self.start_date + "T00:00:00Z"
        if self.end_date:
            url = url + "&until" + self.end_date + "T00:00:00Z"
        logging.info("Loading commits: \t" + url)
        commits = list()

        # TODO: time between commits
        logging.info("Processing page:\t1 / ???")
        response = requests.get(url, headers=headers)
        commits.append(json.loads(response.text)[0])
        if "last" in response.links:
            page_last = int(response.links["last"]["url"].split("=")[-1])
            if self.num_commits > page_last:
                modifier = 1
            else:

                modifier = max(1, (page_last // self.num_commits) - 1)  # step size, must be 1 or higher
            page_current = 1 + modifier
            while page_current <= page_last:
                logging.info("Processing page:\t" + str(page_current) + " / " + str(page_last))
                response = requests.get(url + "&page=" + str(page_current), headers=headers)
                commits.append(json.loads(response.text)[0])
                page_current += modifier
        return commits

    def analyze_class(self, java_class, change, file_path, lines_text, new_lines_not_covered):
        """
        analyze_class - helper function for iterate_classes, takes a given class and git change and compares line coverage
        of added lines.
        :param dict java_class: Java class part of a jacoco report.
        :param tuple change:
        :param file_path:
        :param lines_text:
        :param new_lines_not_covered:
        :return:
        """
        linecache.clearcache()
        class_has_new_uncovered_lines = False
        uncovered_line_dict = dict()
        last_line_nr = 0
        for line in java_class["line"]:
            current_line_nr = int(line["@nr"])
            if current_line_nr in change[1]:  # change[1] = added lines
                if line["@mi"] != "0":
                    new_lines_not_covered += 1
                    if not class_has_new_uncovered_lines:
                        line_text = change[0]
                        logging.info(line_text)
                        lines_text.append(line_text)
                        class_has_new_uncovered_lines = True
                    if last_line_nr + 1 == current_line_nr:  # insert a new line unless lines are next to each other
                        line_text = line["@nr"] + str(linecache.getline(file_path, current_line_nr).rstrip())
                        logging.info(line_text)
                        lines_text.append(line_text)
                    else:
                        line_text = "--------------------------------------------------------------------"
                        logging.info(line_text)
                        lines_text.append(line_text)
                        line_text = line["@nr"] + str(linecache.getline(file_path, current_line_nr).rstrip())
                        logging.info(line_text)
                        lines_text.append(line_text)
                    last_line_nr = current_line_nr
        return lines_text, new_lines_not_covered

    def iterate_classes(self, report_data, change, file_path, lines_text, new_lines_not_covered):
        """
        iterate_classes -           Iterates through the Jacoco report until it finds a
                                    Java class to analyze line coverage of. Used by analyze_diff().
        :param dict report_data:    Jacoco report or a subsection of it.
        :param tuple change:        git diff changes of a single file. Contains (filename, added_lines, deleted_lines)
        :param file_path:           Path of the java file described in "change".
        :param [str, ] lines_text:  List of strings to be printed. Contains line content of uncovered lines in java files.
        :param new_lines_not_covered:   Counts lines added between two commits that weren't covered
        :return: (lines_text, new_lines_not_covered)
        """
        if isinstance(report_data, list):
            for java_class in report_data:
                lines_text, new_lines_not_covered = self.iterate_classes(java_class, change, file_path, lines_text,
                                                                         new_lines_not_covered)
                return lines_text, new_lines_not_covered

        # if there is only one class in report_data["sourcefile"] it is a dict instead of a list of dicts
        if isinstance(report_data["sourcefile"], dict):
            if report_data["sourcefile"]["@name"] == file_path.split("/")[-1]:
                lines_text, new_lines_not_covered = self.analyze_class(report_data["sourcefile"], change, file_path,
                                                                       lines_text,
                                                                       new_lines_not_covered)
        else:
            for java_class in report_data["sourcefile"]:
                try:
                    java_class["@name"]
                except TypeError:
                    logging.info(type(report_data["sourcefile"]))
                    logging.info(report_data)
                    logging.info(java_class)
                if java_class["@name"] == file_path.split("/")[-1]:  # TODO: compare full path
                    lines_text, new_lines_not_covered = self.analyze_class(java_class, change, file_path, lines_text,
                                                                           new_lines_not_covered)
        return lines_text, new_lines_not_covered

    def analyze_diff(self, commit_diff, report_data, lines_text):
        """
        analyze_diffs - Analyzes a given diff between two commits and compares line coverage with the report data from Jacoco.
        :param [(str, int, int), ] commit_diff: Output of a get_commit_diff(). List of tuples with filename, lines added and deleted.
        :param dict report_data: Jacoco report data, created in get_coverage().
        :param str root_path: Root path of this package.
        :param str repo_name: Repository name to be analyzed. Taken from the git_url.
        :param [str, ] lines_text: Lines to be printed after analysis. Contains java lines that aren't covered.
        :return: (uncovered_lines, lines_text): Uncovered_lines contains "new_uncovered_lines", "new_lines" and "new_uncovered_lines_percent"
        """
        uncovered_lines = {"new_uncovered_lines": list(), "new_lines": list(), "new_uncovered_lines_percent": list()}
        new_lines = 0
        new_lines_not_covered = 0
        if not report_data:
            # if report was empty, caused by failed maven execution
            logging.info("Jacoco Report missing. Skipping analysis.")
            return uncovered_lines
        for change in commit_diff:
            # if it's not a java file, skip because we don't have coverage data
            if change[0][-5:] != ".java":
                continue
            new_lines += len(change[1])
            file_path = self.path + "/" + self.repo_name + "/" + change[0]  # change[0] = filename"
            # iterate over java classes in report to find the matching one to the current "change"
            # defined recursively to match changing jacoco.xml format
            lines_text, new_lines_not_covered = self.iterate_classes(report_data["report"]["package"], change,
                                                                     file_path,
                                                                     lines_text, new_lines_not_covered)
        if new_lines == 0:
            new_coverage_percentage = 0.0
        else:
            new_coverage_percentage = new_lines_not_covered / new_lines * 100
        line_text = f"New lines not covered: {new_coverage_percentage:.2f}% \t-\t{new_lines_not_covered} / {new_lines}"
        logging.info(line_text)
        lines_text.append(line_text)

        uncovered_lines["new_uncovered_lines"].append(new_lines_not_covered)
        uncovered_lines["new_lines"].append(new_lines)
        uncovered_lines["new_uncovered_lines_percent"].append(new_coverage_percentage)
        return uncovered_lines, lines_text

    def analyze_file_activity(self, commits=None):
        commit_diff_list = list()
        if not commits:
            commits = self.get_commits()
        last_commit = None
        # ignore first commit in list for testing
        for current_commit in reversed(commits[:-1]):
            if last_commit:
                commit_diff_list.append(self.get_commit_diff(last_commit, current_commit))
            last_commit = current_commit
        module_activity, file_activity, line_activity = self.create_heatmap_data(commit_diff_list)
        num_files = len(line_activity)
        heatmap = list()
        for file_name, file_lines in line_activity.items():
            heatmap.append(file_lines)

        heatmap_files = list()
        heatmap_file_names = list()
        for file_name in sorted(file_activity, key=file_activity.get, reverse=False):
            heatmap_files.append(file_activity[file_name])
            heatmap_file_names.append(file_name.split("/")[-1])

        # transpose heatmap
        heatmap = [list(i) for i in zip(*heatmap)]
        plt.rcParams["figure.figsize"] = (10, 10)

        # fig = plt.figure()
        fig, ax = plt.subplots(2)
        ax[0].pcolormesh(heatmap, cmap="Greys")
        ax[0].set_title("File Activity")
        ax[0].set_xlabel("File")
        ax[0].set_ylabel("Line Number")
        ax[0].set_xticks(ticks=range(num_files), labels=heatmap_file_names)
        ax[0].tick_params(axis="x", labelrotation=8, labelcolor="black", labelsize="small")

        ax[1].barh(range(num_files), heatmap_files)
        ax[1].set_yticks(ticks=range(num_files), labels=heatmap_file_names)
        plt.show()

        # print most common modules
        for module in sorted(module_activity, key=module_activity.get, reverse=True):
            print("Name:\t\t" + module + "\nOccurrence:\t" + str(module_activity[module]))
        # input_string = input("Input Module: (work in progress)\n")

    def get_line_number_coverage(self, jacoco_report):
        covered_line_numbers = dict()
        uncovered_line_numbers = dict()
        for java_class in jacoco_report["package"]["sourcefile"]:
            covered_line_numbers[java_class["@name"]] = list()
            uncovered_line_numbers[java_class["@name"]] = list()
            for line in java_class["line"]:
                if int(line["@ci"]) > 0:
                    covered_line_numbers[java_class["@name"]].append(int(line["@nr"]))
                if int(line["@mi"]) > 0:
                    uncovered_line_numbers[java_class["@name"]].append(int(line["@nr"]))
        logging.info(covered_line_numbers)
        logging.info(uncovered_line_numbers)
        return covered_line_numbers, uncovered_line_numbers

    def get_coverage(self):
        """
        get_coverage -
        :param str git_url: URL of the GitHub repository you want to analyze
        :param str path: Path where the repository and other files will be saved.
        :param str module_path: Path of the module your want to analyze.
        :param str coverage_tool: Optional: Which coverage tool or method to use.
            Currently, "jacoco" or "jacoco-cmd" are accepted.
            "jacoco" edits the pom.xml, "jacoco-cmd" adds jacoco as a parameter at maven execution.
        :param int num_commits: Optional: Number of evenly distributed commits you want to analyze.
        :param str start_date: Optional:Date at which to start analyzing commits in the format YYYY-MM-DD.
        :param str end_date: Optional: Date at which to end analyzing commits in the format YYYY-MM-DD.
        :return: None
        """
        logging.info("Starting get_coverage with following parameters:\n\t\tURL:\t" +
                     self.url + "\n\t\tCoverage Tool:\t" + self.coverage_tool + "\n\t\tNumber of Commits:\t" + str(self.num_commits))
        repo_path = self.path + "\\" + self.repo_name

        commits = self.get_commits()
        coverage_data = {
            "covered": [],
            "missed": [],
            "time": []
        }
        report_data = []
        last_commit = None
        jacoco_report = dict()
        total_uncovered_lines = {"new_uncovered_lines": [], "new_lines": [], "new_uncovered_lines_percent": []}
        total_lines_text = list()
        test_data = {"tests_run": [], "failures": [], "errors": [], "skipped": []}
        commit_diff_list = list()
        heatmap_data = dict()
        df_heatmap = pd.DataFrame

        # iterate through commits, oldest to newest
        for i, current_commit in enumerate(reversed(commits)):
            logging.info("Processing commits:\t" + str(i) + " / " + str(len(commits)))
            commit_hash = current_commit["sha"]
            commit_date = current_commit["commit"]["author"]["date"]
            line_text = "Commit ID:\t" + commit_hash + "\n" + "Date:\t\t" + commit_date
            logging.info(line_text)
            lines_text = [line_text]

            logging.info("Changing path to " + repo_path)
            os.chdir(repo_path)
            logging.info("Switching to commit:\t" + commit_hash)
            subprocess.run("git clean -df")  # discards all changes
            subprocess.run("git restore .")  # discard all changes
            subprocess.run("git checkout -f " + commit_hash)  # switches to different commit

            if self.module_path:
                if os.path.exists(self.module_path):
                    logging.info("Changing path to:\t" + self.module_path)
                    os.chdir(self.module_path)
                else:
                    logging.info("Module missing. Skipping commit.")
                    continue

            if self.coverage_tool:
                pom_paths = find_pom(os.getcwd())
                if pom_paths and (self.coverage_tool == "jacoco" or self.coverage_tool == "jacoco-aggregate"):
                    # insert jacoco in pom.xml
                    exit_code = adjust_pom(pom_paths[0], self.coverage_tool, version="0.8.10", is_main_module=True)
                    logging.info("Main pom.xml path: %s", pom_paths[0])
                    # if pom.xml couldn't be adjusted because of parsing errors, skip to next commit
                    if exit_code:
                        continue
                    if len(pom_paths) > 1:  # if multiple poms were found
                        for pom in pom_paths[1:]:
                            exit_code = adjust_pom(pom, is_main_module=False)
                            if exit_code:
                                continue
                # if pom.xml couldn't be found and we don't use jacoco-cmd
                elif not pom_paths:
                    logging.info("No pom.xml found in commit: " + commit_hash)
                    report_data.append(None)
                    continue
                logging.info("Changing path to:\n" + pom_paths[0])
                os.chdir(pom_paths[0])

            output = b""
            if self.coverage_tool == "jacoco" or self.coverage_tool == "jacoco-aggregate":
                output = subprocess.check_output(["mvn.cmd", "clean", "verify", "-fn"])
            if self.coverage_tool == "jacoco-cmd":
                output = subprocess.check_output(["mvn.cmd",
                                                  "clean",
                                                  "-Djacoco.skip=false",
                                                  "org.jacoco:jacoco-maven-plugin:0.8.10:prepare-agent",
                                                  "verify",
                                                  "-fn",
                                                  "org.jacoco:jacoco-maven-plugin:0.8.10:report-aggregate"])
            try:
                output = output.decode(encoding="utf-8")
                print(output)
                # find all test results
                if not output.find("Results") == -1:  # only false for build failures
                    results = output[output.find("Results"):].split(", ")
                    # skip the text "Tests run: " to get to the number
                    tests_run = int(results[0][results[0].find("Tests run:") + 11:])
                    failures = int(results[1][10:])
                    errors = int(results[2][8:])
                    # split skipped from the rest of the output. Wasn't comma separated.
                    skipped = int(results[3].split("\r")[0][9:])

                    test_data["tests_run"].append(tests_run)
                    test_data["failures"].append(failures)
                    test_data["errors"].append(errors)
                    test_data["skipped"].append(skipped)
                end = output[output.find("Total time:"):].split("\n")
                total_time = end[0][13:]
                finished_at = end[1][20:]
                print(total_time)
                print(finished_at)
            except UnicodeDecodeError:
                logging.info("Error decoding maven execution output.")

            if self.coverage_tool:
                if self.coverage_tool == "jacoco" or self.coverage_tool == "jacoco-aggregate":
                    if not os.path.exists("./target/jacoco-ut"):
                        logging.info("Jacoco folder missing. Maven execution failed or got skipped.")
                        report_data.append(None)
                        continue
                    os.chdir("./target/jacoco-ut/")
                elif self.coverage_tool == "jacoco-cmd":
                    if not os.path.exists("./target/site/jacoco"):
                        logging.info("Jacoco folder missing. Maven execution failed or got skipped.")
                        report_data.append(None)
                        continue
                    os.chdir("./target/site/jacoco")

                logging.info("Changing path to:\n" + os.getcwd())

                # read xml to dict
                try:
                    with open("jacoco.xml", "r", encoding="utf-8") as file:
                        my_xml = file.read()
                    jacoco_report = xmltodict.parse(my_xml)
                    report_data.append(jacoco_report)

                    covered = int(jacoco_report["report"]["counter"][0]["@covered"])
                    missed = int(jacoco_report["report"]["counter"][0]["@missed"])
                    coverage_data["covered"].append(covered)
                    coverage_data["missed"].append(missed)
                    coverage_data["time"].append(commit_date)
                    line_number_coverage = self.get_line_number_coverage(jacoco_report["report"])

                except IOError:
                    logging.info("jacoco.xml doesn't exist.")
            if last_commit:
                commit_diff = self.get_commit_diff(last_commit, current_commit)
                commit_diff_list.append(commit_diff)
                heatmap_data = self.create_heatmap_data(commit_diff_list, line_number_coverage)
                df_heatmap = self.new_create_heatmap_data(commit_diff_list, line_number_coverage)
                uncovered_lines, lines_text = self.analyze_diff(commit_diff, jacoco_report, lines_text)
                # merge old results with new results
                total_uncovered_lines = {key: total_uncovered_lines.get(key, []) + uncovered_lines.get(key, []) for key
                                         in
                                         set(list(total_uncovered_lines.keys()) + list(uncovered_lines.keys()))}
                # if lines_text only contains the commit id and date, skip appending
                if not len(lines_text) == 1:
                    lines_text.append("\n")
                    total_lines_text.append(lines_text)
            last_commit = current_commit
        for lines in total_lines_text:
            for line in lines:
                print(line)

        if not os.path.exists(self.path + "/cache/"):
            os.makedirs(self.path + "/cache")
        os.chdir(self.path + "/cache/")
        # create copy of data for testing
        with open(self.repo_name + "_coverage_data", "wb") as file:
            pickle.dump(coverage_data, file)
        with open(self.repo_name + "_total_uncovered_lines", "wb") as file:
            pickle.dump(total_uncovered_lines, file)
        with open(self.repo_name + "_total_lines_text", "wb") as file:
            pickle.dump(total_lines_text, file)
        with open(self.repo_name + "_test_data", "wb") as file:
            pickle.dump(test_data, file)
        with open(self.repo_name + "_heatmap_data", "wb") as file:
            pickle.dump(heatmap_data, file)
        with open(self.repo_name + "_df_heatmap", "wb") as file:
            pickle.dump(df_heatmap, file)
        return
