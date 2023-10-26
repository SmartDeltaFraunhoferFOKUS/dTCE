"""PyCoverageAnalyzer

PyCoverageAnalyzer is a package that analyzes Java GitHub repositories using Maven and Jacoco.

Requirements:
    The repository to be analyzed uses Java and Maven.

    Java, Maven and Git are installed and on the Path, meaning they can be executed from a terminal by calling java, mvn and git.

    Java and Maven versions have to match what is required for the repository to be executed. An older version might be required for older commits or branches.

    A GitHub API token, for higher rate limits and access to private repositories.

    Python requirements are included in the setup.py but are
        * xmltodict
        * matplotlib
        * requests
        * unidiff

Example:
    url = "https://github.com/junit-team/junit4"
    PyCoverageAnalyzer.get_coverage(url)
    """
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

# check if git and mvn are installed and findable
maven_check = subprocess.check_output("mvn.cmd -version").decode("utf-8").split(" ")
if maven_check[0] == "Apache":
    logging.info("Maven is installed. Version " + maven_check[2])
else:
    logging.info("Maven is not installed or not on PATH. "
                 "Install Maven so that it can be started with 'mvn -v' or 'mvn.cmd -v' on a terminal.")
git_check = subprocess.check_output("git --version").decode("utf-8").split(" ")
if git_check[0] == "git":
    logging.info("Git is installed. Version: " + git_check[2])
else:
    logging.info("Git is not installed or not on PATH."
                 "Install Git so that it can be started with 'git -v' on a terminal.")

