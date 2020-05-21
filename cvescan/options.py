import os
import re

import cvescan.constants as const
from cvescan.errors import ArgumentError

FMT_CVE_OPTION = "-c|--cve"
FMT_EXPERIMENTAL_OPTION = "-x|--experimental"
FMT_FILE_OPTION = "-f|--file"
FMT_MANIFEST_OPTION = "-m|--manifest"
FMT_NAGIOS_OPTION = "-n|--nagios"
FMT_UCT_LINKS_OPTION = "--uct-links"
FMT_OVAL_FILE_OPTION = "-o|--oval_file"
FMT_PRIORITY_OPTION = "-p|priority"
FMT_SILENT_OPTION = "-s|--silent"
FMT_UNRESOLVED_OPTION = "--unresolved"
FMT_VERBOSE_OPTION = "-v|--verbose"

MANIFEST_URL_TEMPLATE = (
    "https://cloud-images.ubuntu.com/%s/current/%s-server-cloudimg-amd64.manifest"
)


class Options:
    def __init__(self, args, sysinfo):
        raise_on_invalid_args(args)

        self._set_mode(args)
        self._set_distrib_codename(args, sysinfo)
        self._set_oval_file_options(args, sysinfo)
        self._set_manifest_file_options(args)
        self._set_output_verbosity(args)

        self.cve = args.cve
        self.priority = args.priority
        self.unresolved = args.unresolved

        self.uct_links = args.uct_links

    def _set_mode(self, args):
        self.manifest_mode = True if args.manifest else False
        self.experimental_mode = args.experimental
        self.nagios_mode = args.nagios

    def _set_distrib_codename(self, args, sysinfo):
        if self.manifest_mode:
            self.distrib_codename = args.manifest
        else:
            self.distrib_codename = sysinfo.distrib_codename

    def _set_oval_file_options(self, args, sysinfo):
        self.oval_base_url = None

        if args.oval_file:
            self.oval_file = args.oval_file
            return

        self.oval_base_url = "https://people.canonical.com/~ubuntu-security/oval"
        self.oval_file = "com.ubuntu.%s.cve.oval.xml" % self.distrib_codename

        if self.manifest_mode:
            self.oval_file = "oci.%s" % self.oval_file

        if self.experimental_mode:
            self.oval_base_url = "%s/alpha" % self.oval_base_url
            self.oval_file = "alpha.%s" % self.oval_file

        self.oval_zip = "%s.bz2" % self.oval_file

    def _set_manifest_file_options(self, args):
        manifest_url_tmp = MANIFEST_URL_TEMPLATE % (
            self.distrib_codename,
            self.distrib_codename,
        )

        self.manifest_file = os.path.abspath(args.file) if args.file else None
        self.manifest_url = (
            manifest_url_tmp if (self.manifest_mode and not args.file) else None
        )

    def _set_output_verbosity(self, args):
        self.verbose_oscap_options = ""

        if args.verbose:
            self.verbose_oscap_options = (
                "--verbose WARNING --verbose-log-file %s" % const.DEBUG_LOG
            )

    @property
    def download_oval_file(self):
        return self.oval_base_url is not None


def raise_on_invalid_args(args):
    raise_on_invalid_cve(args)
    raise_on_invalid_combinations(args)
    raise_on_missing_manifest_file(args)
    raise_on_missing_oval_file(args)


def raise_on_invalid_cve(args):
    cve_regex = r"^CVE-[0-9]{4}-[0-9]{4,}$"
    if (args.cve is not None) and (not re.match(cve_regex, args.cve)):
        raise ValueError("Invalid CVE ID (%s)" % args.cve)


def raise_on_invalid_combinations(args):
    raise_on_invalid_manifest_options(args)
    raise_on_invalid_nagios_options(args)
    raise_on_invalid_silent_options(args)
    raise_on_invalid_unresolved_options(args)


def raise_on_invalid_manifest_options(args):
    if args.file and not args.manifest:
        raise ArgumentError("Cannot specify -f|--file argument without -m|--manifest.")


def raise_on_invalid_nagios_options(args):
    if not args.nagios:
        return

    if args.cve:
        raise_incompatible_arguments_error(FMT_NAGIOS_OPTION, FMT_CVE_OPTION)

    if args.silent:
        raise_incompatible_arguments_error(FMT_NAGIOS_OPTION, FMT_SILENT_OPTION)

    if args.unresolved:
        raise_incompatible_arguments_error(FMT_NAGIOS_OPTION, FMT_UNRESOLVED_OPTION)

    if args.uct_links:
        raise_incompatible_arguments_error(FMT_NAGIOS_OPTION, FMT_UCT_LINKS_OPTION)


def raise_on_invalid_silent_options(args):
    if not args.silent:
        return

    if not args.cve:
        raise ArgumentError(
            "Cannot specify %s argument without %s."
            % (FMT_SILENT_OPTION, FMT_CVE_OPTION)
        )

    if args.verbose:
        raise_incompatible_arguments_error(FMT_SILENT_OPTION, FMT_VERBOSE_OPTION)

    if args.uct_links:
        raise_incompatible_arguments_error(FMT_SILENT_OPTION, FMT_UCT_LINKS_OPTION)


def raise_on_invalid_unresolved_options(args):
    if args.unresolved and args.cve:
        raise_incompatible_arguments_error(FMT_UNRESOLVED_OPTION, FMT_CVE_OPTION)

    if args.unresolved and args.nagios:
        raise_incompatible_arguments_error(FMT_UNRESOLVED_OPTION, FMT_NAGIOS_OPTION)


def raise_incompatible_arguments_error(arg1, arg2):
    raise ArgumentError(
        "The %s and %s options are incompatible and may not "
        "be specified together." % (arg1, arg2)
    )


def raise_on_missing_manifest_file(args):
    raise_on_missing_file(args.file)


def raise_on_missing_oval_file(args):
    raise_on_missing_file(args.oval_file)


def raise_on_missing_file(file_path):
    if not file_path:
        return

    file_abs_path = os.path.abspath(file_path)
    if not os.path.isfile(file_abs_path):
        # TODO: mention snap confinement in error message
        raise ArgumentError(
            'Cannot find file "%s". Current '
            'working directory is "%s".' % (file_abs_path, os.getcwd())
        )
