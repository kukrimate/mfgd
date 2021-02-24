from django.http import HttpResponse
from django.shortcuts import render
from pathlib import Path
import pygit2

from mfgd_app import utils
from mfgd_app.utils import ObjectType

# Directory
BASE_DIR = Path(__file__).resolve().parent.parent
# Repo
repo = pygit2.Repository(BASE_DIR / ".git")


def format_author(commit):
    return "%s <%s>" % (commit.author.name, commit.author.email)


def str_tree(tree, indent=0):
    r = ""
    for obj in tree:
        r += "  " * indent + obj.name + "\n"
        if obj.type_str == "tree":
            r += str_tree(obj, indent + 1)
    return r


def index(request):
    branch = next(iter(repo.branches.local))
    branch_ref = repo.references["refs/heads/%s" % branch]

    r = ""
    for commit in repo.walk(branch_ref.target, GIT_SORT_TOPOLOGICAL):
        r += "%s\n%s\n%s\n" % (commit.oid, format_author(commit), commit.message)
        r += str_tree(commit.tree)
        r += "\n"

    return HttpResponse(r, content_type="text/plain")


def tree(request, commit, path):
    context = {}

    try:
        commit = repo.get(commit)
        if commit.type_str != "commit":
            raise ValueError()
    except:
        return HttpResponse("Invalid commit id")

    entry = utils.resolve_path(commit.tree, path)
    if entry is None or entry.type != ObjectType.TREE:
        return HttpResponse("invalid path")

    context["entries"] = entry
    context["repo"] = repo
    context["path"] = request.path + ("" if request.path[-1:] == "/" else "/")
    context["depth"] = len(path.strip("/").split("/"))
    return render(request, "tree.html", context=context)


def blob(request, commit, path):
    ctx = {}

    try:
        obj = repo.get(commit)
        if obj.type_str != "commit":
            raise ValueError()
    except:
        return HttpResponse("Invalid commit id")

    try:
        blob = obj.tree[path]
        if blob.type_str != "blob":
            raise ValueError()
    except:
        return HttpResponse("Path does not point to a blob")

    ctx["code"] = blob.data.decode()
    return render(request, "blob.html", context=ctx)
