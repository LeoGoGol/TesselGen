
import errno
import os
import re
import subprocess
import sys


def get_keywords():

    git_refnames = " (HEAD -> main, tag: v0.2.0)"
    git_full = "ee2adf0068a5fc5fa2c83043d1db31c2df47ed1b"
    git_date = "2020-11-07 02:42:45 +0100"
    keywords = {"refnames": git_refnames, "full": git_full, "date": git_date}
    return keywords

class VersioneerConfig:

def get_config():

    cfg = VersioneerConfig()
    cfg.VCS = "git"
    cfg.style = "pep440-post"
    cfg.tag_prefix = "v"
    cfg.parentdir_prefix = "None"
    cfg.versionfile_source = "polygonation/_version.py"
    cfg.verbose = False
    return cfg

class NotThisMethod(Exception):

LONG_VERSION_PY = {}
HANDLERS = {}

def register_vcs_handler(vcs, method):  # decorator

    def decorate(f):
        """Store f in HANDLERS[vcs][method]."""
        if vcs not in HANDLERS:
            HANDLERS[vcs] = {}
        HANDLERS[vcs][method] = f
        return f

    return decorate


def run_command(commands, args, cwd=None, verbose=False, hide_stderr=False, env=None):

    assert isinstance(commands, list)
    p = None
    for c in commands:
        try:
            dispcmd = str([c] + args)
            # remember shell=False, so use git.cmd on windows, not just git
            p = subprocess.Popen(
                [c] + args,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=(subprocess.PIPE if hide_stderr else None),
            )
            break
        except EnvironmentError:
            e = sys.exc_info()[1]
            if e.errno == errno.ENOENT:
                continue
            if verbose:
                print("unable to run %s" % dispcmd)
                print(e)
            return None, None
    else:
        if verbose:
            print("unable to find command, tried %s" % (commands,))
        return None, None
    stdout = p.communicate()[0].strip()
    if sys.version_info[0] >= 3:
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %s (error)" % dispcmd)
            print("stdout was %s" % stdout)
        return None, p.returncode
    return stdout, p.returncode


def versions_from_parentdir(parentdir_prefix, root, verbose):

    rootdirs = []

    for i in range(3):
        dirname = os.path.basename(root)
        if dirname.startswith(parentdir_prefix):
            return {
                "version": dirname[len(parentdir_prefix) :],
                "full-revisionid": None,
                "dirty": False,
                "error": None,
                "date": None,
            }
        else:
            rootdirs.append(root)
            root = os.path.dirname(root)  # up a level

    if verbose:
        print(
            "Tried directories %s but none started with prefix %s"
            % (str(rootdirs), parentdir_prefix)
        )
    raise NotThisMethod("rootdir doesn't start with parentdir_prefix")


@register_vcs_handler("git", "get_keywords")
def git_get_keywords(versionfile_abs):

    keywords = {}
    try:
        f = open(versionfile_abs, "r")
        for line in f.readlines():
            if line.strip().startswith("git_refnames ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    keywords["refnames"] = mo.group(1)
            if line.strip().startswith("git_full ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    keywords["full"] = mo.group(1)
            if line.strip().startswith("git_date ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    keywords["date"] = mo.group(1)
        f.close()
    except EnvironmentError:
        pass
    return keywords


@register_vcs_handler("git", "keywords")
def git_versions_from_keywords(keywords, tag_prefix, verbose):
    """Get version information from git keywords."""
    if not keywords:
        raise NotThisMethod("no keywords at all, weird")
    date = keywords.get("date")
    if date is not None:

        date = date.strip().replace(" ", "T", 1).replace(" ", "", 1)
    refnames = keywords["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("keywords are unexpanded, not using")
        raise NotThisMethod("unexpanded keywords, not a git-archive tarball")
    refs = set([r.strip() for r in refnames.strip("()").split(",")])

    TAG = "tag: "
    tags = set([r[len(TAG) :] for r in refs if r.startswith(TAG)])
    if not tags:

        tags = set([r for r in refs if re.search(r"\d", r)])
        if verbose:
            print("discarding '%s', no digits" % ",".join(refs - tags))
    if verbose:
        print("likely tags: %s" % ",".join(sorted(tags)))
    for ref in sorted(tags):

        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix) :]
            if verbose:
                print("picking %s" % r)
            return {
                "version": r,
                "full-revisionid": keywords["full"].strip(),
                "dirty": False,
                "error": None,
                "date": date,
            }
    # no suitable tags, so version is "0+unknown", but full hex is still there
    if verbose:
        print("no suitable tags, using unknown + full revision id")
    return {
        "version": "0+unknown",
        "full-revisionid": keywords["full"].strip(),
        "dirty": False,
        "error": "no suitable tags",
        "date": None,
    }


@register_vcs_handler("git", "pieces_from_vcs")
def git_pieces_from_vcs(tag_prefix, root, verbose, run_command=run_command):

    GITS = ["git"]
    if sys.platform == "win32":
        GITS = ["git.cmd", "git.exe"]

    out, rc = run_command(GITS, ["rev-parse", "--git-dir"], cwd=root, hide_stderr=True)
    if rc != 0:
        if verbose:
            print("Directory %s not under git control" % root)
        raise NotThisMethod("'git rev-parse --git-dir' returned error")

    describe_out, rc = run_command(
        GITS,
        [
            "describe",
            "--tags",
            "--dirty",
            "--always",
            "--long",
            "--match",
            "%s*" % tag_prefix,
        ],
        cwd=root,
    )
    # --long was added in git-1.5.5
    if describe_out is None:
        raise NotThisMethod("'git describe' failed")
    describe_out = describe_out.strip()
    full_out, rc = run_command(GITS, ["rev-parse", "HEAD"], cwd=root)
    if full_out is None:
        raise NotThisMethod("'git rev-parse' failed")
    full_out = full_out.strip()

    pieces = {}
    pieces["long"] = full_out
    pieces["short"] = full_out[:7]  # maybe improved later
    pieces["error"] = None

    git_describe = describe_out

    dirty = git_describe.endswith("-dirty")
    pieces["dirty"] = dirty
    if dirty:
        git_describe = git_describe[: git_describe.rindex("-dirty")]

    if "-" in git_describe:

        mo = re.search(r"^(.+)-(\d+)-g([0-9a-f]+)$", git_describe)
        if not mo:

            pieces["error"] = "unable to parse git-describe output: '%s'" % describe_out
            return pieces


        full_tag = mo.group(1)
        if not full_tag.startswith(tag_prefix):
            if verbose:
                fmt = "tag '%s' doesn't start with prefix '%s'"
                print(fmt % (full_tag, tag_prefix))
            pieces["error"] = "tag '%s' doesn't start with prefix '%s'" % (
                full_tag,
                tag_prefix,
            )
            return pieces
        pieces["closest-tag"] = full_tag[len(tag_prefix) :]

        pieces["distance"] = int(mo.group(2))

        pieces["short"] = mo.group(3)

    else:

        pieces["closest-tag"] = None
        count_out, rc = run_command(GITS, ["rev-list", "HEAD", "--count"], cwd=root)
        pieces["distance"] = int(count_out)  # total number of commits


    date = run_command(GITS, ["show", "-s", "--format=%ci", "HEAD"], cwd=root)[
        0
    ].strip()
    pieces["date"] = date.strip().replace(" ", "T", 1).replace(" ", "", 1)

    return pieces


def plus_or_dot(pieces):

    if "+" in pieces.get("closest-tag", ""):
        return "."
    return "+"


def render_pep440(pieces):

    if pieces["closest-tag"]:
        rendered = pieces["closest-tag"]
        if pieces["distance"] or pieces["dirty"]:
            rendered += plus_or_dot(pieces)
            rendered += "%d.g%s" % (pieces["distance"], pieces["short"])
            if pieces["dirty"]:
                rendered += ".dirty"
    else:
        # exception #1
        rendered = "0+untagged.%d.g%s" % (pieces["distance"], pieces["short"])
        if pieces["dirty"]:
            rendered += ".dirty"
    return rendered


def render_pep440_pre(pieces):

    if pieces["closest-tag"]:
        rendered = pieces["closest-tag"]
        if pieces["distance"]:
            rendered += ".post.dev%d" % pieces["distance"]
    else:

        rendered = "0.post.dev%d" % pieces["distance"]
    return rendered


def render_pep440_post(pieces):

    if pieces["closest-tag"]:
        rendered = pieces["closest-tag"]
        if pieces["distance"] or pieces["dirty"]:
            rendered += ".post%d" % pieces["distance"]
            if pieces["dirty"]:
                rendered += ".dev0"
            rendered += plus_or_dot(pieces)
            rendered += "g%s" % pieces["short"]
    else:

        rendered = "0.post%d" % pieces["distance"]
        if pieces["dirty"]:
            rendered += ".dev0"
        rendered += "+g%s" % pieces["short"]
    return rendered


def render_pep440_old(pieces):

    if pieces["closest-tag"]:
        rendered = pieces["closest-tag"]
        if pieces["distance"] or pieces["dirty"]:
            rendered += ".post%d" % pieces["distance"]
            if pieces["dirty"]:
                rendered += ".dev0"
    else:
        # exception #1
        rendered = "0.post%d" % pieces["distance"]
        if pieces["dirty"]:
            rendered += ".dev0"
    return rendered


def render_git_describe(pieces):

    if pieces["closest-tag"]:
        rendered = pieces["closest-tag"]
        if pieces["distance"]:
            rendered += "-%d-g%s" % (pieces["distance"], pieces["short"])
    else:
        # exception #1
        rendered = pieces["short"]
    if pieces["dirty"]:
        rendered += "-dirty"
    return rendered


def render_git_describe_long(pieces):

    if pieces["closest-tag"]:
        rendered = pieces["closest-tag"]
        rendered += "-%d-g%s" % (pieces["distance"], pieces["short"])
    else:
        # exception #1
        rendered = pieces["short"]
    if pieces["dirty"]:
        rendered += "-dirty"
    return rendered


def render(pieces, style):

    if pieces["error"]:
        return {
            "version": "unknown",
            "full-revisionid": pieces.get("long"),
            "dirty": None,
            "error": pieces["error"],
            "date": None,
        }

    if not style or style == "default":
        style = "pep440"  # the default

    if style == "pep440":
        rendered = render_pep440(pieces)
    elif style == "pep440-pre":
        rendered = render_pep440_pre(pieces)
    elif style == "pep440-post":
        rendered = render_pep440_post(pieces)
    elif style == "pep440-old":
        rendered = render_pep440_old(pieces)
    elif style == "git-describe":
        rendered = render_git_describe(pieces)
    elif style == "git-describe-long":
        rendered = render_git_describe_long(pieces)
    else:
        raise ValueError("unknown style '%s'" % style)

    return {
        "version": rendered,
        "full-revisionid": pieces["long"],
        "dirty": pieces["dirty"],
        "error": None,
        "date": pieces.get("date"),
    }


def get_versions():

    cfg = get_config()
    verbose = cfg.verbose

    try:
        return git_versions_from_keywords(get_keywords(), cfg.tag_prefix, verbose)
    except NotThisMethod:
        pass

    try:
        root = os.path.realpath(__file__)

        for i in cfg.versionfile_source.split("/"):
            root = os.path.dirname(root)
    except NameError:
        return {
            "version": "0+unknown",
            "full-revisionid": None,
            "dirty": None,
            "error": "unable to find root of source tree",
            "date": None,
        }

    try:
        pieces = git_pieces_from_vcs(cfg.tag_prefix, root, verbose)
        return render(pieces, cfg.style)
    except NotThisMethod:
        pass

    try:
        if cfg.parentdir_prefix:
            return versions_from_parentdir(cfg.parentdir_prefix, root, verbose)
    except NotThisMethod:
        pass

    return {
        "version": "0+unknown",
        "full-revisionid": None,
        "dirty": None,
        "error": "unable to compute version",
        "date": None,
    }