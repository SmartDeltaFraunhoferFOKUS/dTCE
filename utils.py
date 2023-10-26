import os
import logging
from xml.etree import ElementTree as ET


def find_pom(path):
    """
    find_pom - Finds the first pom.xml and return the folder its located in.
    :param str path: Path in which to search for a pom.xml for.
    :return: Path to the folder containing a pom.xml file.
    """
    pom_list = list()
    for root, dirs, files in os.walk(path):
        if "pom.xml" in files:
            pom_list.append(root)
    return pom_list


def findall(p, s):
    """Yields all the positions of
    the pattern p in the string s."""
    i = s.find(p)
    while i != -1:
        yield i
        i = s.find(p, i + 1)


def adjust_pom(root_path, coverage_tool="jacoco", version="0.8.10", is_main_module=True):
    """
    adjust_pom - Edits the pom.xml, if it exists, to include jacoco during maven execution and create a code coverage report.
    :param str root_path: Root path of this package.
    :param str coverage_tool: Currently unused.
    :param str version: Jacoco version you want to set.
    :param bool is_main_module: Value if the current pom.xml is the main maven file of the project. Submodules just need
    Surefire adjustments.
    :return:
    """
    root_path = root_path + "/"
    try:
        if os.path.exists(root_path + "pom.xml.backup"):
            tree = ET.parse(root_path + "pom.xml.backup")
        else:
            tree = ET.parse(root_path + "pom.xml")
            tree.write(root_path + "pom.xml.backup")
    except ET.ParseError:
        logging.info("The pom.xml file is not well-formed and couldn't be parsed correctly. Skipping Execution.")
        return 1
    root = tree.getroot()
    # find and register namespace
    namespace = root.tag[0:root.tag.find("}") + 1]
    ET.register_namespace('', namespace[1:-1])

    found_surefire = False
    found_jacoco = False
    build = root.find(namespace + "build")

    if build is not None:
        plugins = build.find(namespace + "plugins")
        # if "plugins" doesn't exist in build, try different pom.xml structures
        if not plugins:
            plugin_management = build.find(namespace + "pluginManagement")
            if plugin_management:
                plugins = plugin_management.find(namespace + "plugins")
            else:
                plugins = ET.Element("plugins")
                build.append(plugins)
    else:
        logging.info("Couldn't find build location in pom.xml. Build location is being added.")
        new_build = ET.Element(namespace + "build")
        plugins = ET.Element(namespace + "plugins")
        # new_build.append(new_plugins)
        root.append(new_build)
        root.find(namespace + "build").append(plugins)
        # logging.info(root.find(namespace + "build"))
        # logging.info(root.find(namespace + "build").find(namespace + "plugins"))
        # plugins = root.find(namespace + "build").find(namespace + "plugins")
        # if not plugins:
        #     logging.info(root_path)
        # logging.info("Couldn't find build location in pom.xml. Jacoco couldn't be added.")
        # return 1

    if plugins:
        for plugin in plugins.findall(namespace + "plugin"):
            # logging.info(plugin.find(namespace + "artifactId").text)
            # if plugin.find(namespace + "artifactId").text == "maven-compiler-plugin":
            #     if plugin.find(namespace + "configuration").find(namespace + "source")
            if plugin.find(namespace + "artifactId").text == "jacoco-maven-plugin":
                logging.info("Found jacoco-maven-plugin")
                found_jacoco = True
            if plugin.find(namespace + "artifactId").text == "maven-surefire-plugin":
                logging.info("Found maven-surefire-plugin")
                found_argline = False
                if plugin.find(namespace + "configuration"):
                    for config in plugin.find(namespace + "configuration"):
                        if config.tag[len(namespace):] == "argLine":
                            found_argline = True
                            # logging.info("Removing argLine")
                            # plugin.find(namespace + "configuration").remove(config)
                            plugin.find(namespace + "configuration").find(
                                namespace + "argLine").text = "${surefireArgLine}"  # TODO prepend surefireargsline instead of overwriting?
                else:
                    logging.info("Creating configuration and surefire plugin.")
                    new_element = ET.Element(namespace + "configuration")
                    plugin.append(new_element)
                if not found_argline:
                    new_element = ET.fromstring("<argLine>${surefireArgLine}</argLine>")
                    plugin.find(namespace + "configuration").append(new_element)
                new_element = ET.fromstring("<testFailureIgnore>true</testFailureIgnore>")
                plugin.find(namespace + "configuration").append(new_element)
                found_surefire = True
    elif is_main_module:
        logging.info("Couldn't find plugin locations in pom.xml. Jacoco couldn't be added.")
        return 1
    else:
        # logging.info("Plugins location not found.")
        pass

    if not found_jacoco and is_main_module:
        # add jacoco version variable
        new_property = ET.Element("jacoco.version")
        new_property.text = version
        property_entry_point = root.find(namespace + "properties")
        if property_entry_point is None:
            new_parent_property = ET.Element("properties")
            root.append(new_parent_property)
            property_entry_point = root.find("properties")
        property_entry_point.append(new_property)
        new_property = ET.Element("jacoco.reportPath")
        new_property.text = "${project.basedir}/../target/jacoco.exec"

        element_string = ''' <plugin>
            <groupId>org.jacoco</groupId>
            <artifactId>jacoco-maven-plugin</artifactId>
            <version>${jacoco.version}</version>
            <executions>
              <!-- Prepares the property pointing to the JaCoCo runtime agent which
                  is passed as VM argument when Maven the Surefire plugin is executed. -->
              <execution>
                <id>pre-unit-test</id>
                <goals>
                  <goal>prepare-agent</goal>
                </goals>
                <configuration>
                  <!-- Sets the name of the property containing the settings for JaCoCo
                      runtime agent. -->
                  <propertyName>surefireArgLine</propertyName>
                  <append>true</append>
                  <destFile>${jacoco.reportPath}</destFile>
                </configuration>
              </execution>
              <!-- Ensures that the code coverage report for unit tests is created
                  after unit tests have been run. -->
              <execution>
                <id>post-unit-test</id>
                <phase>test</phase>
                <goals>
                  <goal>report</goal>
                </goals>
                <configuration>
                  <!-- Sets the output directory for the code coverage report. -->
                  <outputDirectory>./target/jacoco-ut/</outputDirectory>
                  <includeCurrentProject>true</includeCurrentProject>
                </configuration>
              </execution>
            </executions>
        </plugin>'''
        if coverage_tool == "jacoco-aggregate":
            # change goal "report" to "report
            element_string.replace("report", "report-aggregate")
        new_element = ET.fromstring(element_string)
        plugins.append(new_element)

    if not found_surefire:
        new_element = ET.fromstring("""
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-surefire-plugin</artifactId>
            <version>2.19.1</version>
            <configuration>
              <!-- Sets the VM argument line used when unit tests are run. -->
              <argLine>${surefireArgLine}</argLine>
              <testFailureIgnore>true</testFailureIgnore>
            </configuration>
        </plugin>
        """)
        plugins.append(new_element)
    ET.register_namespace('', "http://maven.apache.org/POM/4.0.0")
    tree.write(root_path + "pom.xml", encoding="utf-8", xml_declaration=True, method="xml")
    return 0

