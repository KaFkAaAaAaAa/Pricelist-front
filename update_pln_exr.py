#!/usr/bin/env python3
import requests
import xml.etree.ElementTree as ET
import datetime


def _get_date_from_filename(filename):
    return datetime.date.fromisoformat("20" + filename[-6:])


def is_newer_available(filename):
    latest = _get_newest_filename()
    if _get_date_from_filename(latest) > _get_date_from_filename(filename):
        return latest
    else:
        return False


def _get_newest_filename():
    response = requests.get("https://static.nbp.pl/dane/kursy/xml/dir.txt")
    latest = response.text.rsplit("\n", 1)
    while latest[-1][0] != "a":
        latest = latest[0].rstrip().rsplit("\n", 1)
    return latest[-1]


def get_exr_from_filename(latest):
    current_nbp = requests.get(f"https://static.nbp.pl/dane/kursy/xml/{latest}.xml")

    # with open(f'courses/pln/{latest}.xml', 'wb') as f:
    #     f.write(current_nbp.content)
    root = ET.fromstring(current_nbp.content)
    for element in root.findall("pozycja"):
        code = element.find("kod_waluty").text
        if code == "EUR":
            output = float(element.find("kurs_sredni").text.replace(",", "."))
            return output


def main():
    with open("pln_exr.txt", "r") as f:
        read_exr = f.read()
    read_exr = read_exr.split("\t")
    newer = is_newer_available(read_exr[0])
    if newer:
        with open("pln_exr.txt", "w") as f:
            f.write(f"{newer}\t{get_exr_from_filename(newer)}")


if __name__ == "__main__":
    main()
