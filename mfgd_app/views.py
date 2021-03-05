import binascii

from django.http import HttpResponse
from django.shortcuts import render
from django import urls
from pathlib import Path
import pygit2

from mfgd_app import utils
from mfgd_app.types import ObjectType, TreeEntry
from mfgd_app.models import Repository

# Directory
BASE_DIR = Path(__file__).resolve().parent.parent
# Repo
repo = pygit2.Repository(BASE_DIR / ".git")

def index(request):
    context_dict = {}
    repo_list = Repository.objects.all()
    for i, rep in enumerate(repo_list):
        repo_list[i].description = repo_list[i].description[0:30] # Only select the first 30 chacters in case of overflow
    context_dict['repositories'] = repo_list # Load the repos data here
    return render(request, 'index.html', context_dict)

def read_blob(blob):
    MAX_BLOB_SIZE = 100 * 1 << 10   # 100K

    content = blob.data
    if blob.is_binary:
        if blob.size > MAX_BLOB_SIZE:
            return "blob_binary.html", ""
        return "blob_binary.html", utils.hex_dump(content)
    else:
        if blob.size > MAX_BLOB_SIZE:
            return "blob.html", ""
    return "blob.html", content.decode()


def gen_crumbs(oid, path):
    class Crumb:
        def __init__(self, name, url):
            self.name = name
            self.url = url

        def __str__(self):
            return self.name

    crumbs = []
    parts = utils.split_path(path)
    for off in range(len(parts)):
        relative_path = "/".join(parts[:off + 1]) + "/"
        url = urls.reverse("view",
                kwargs={"oid": oid, "path": relative_path})
        crumbs.append(Crumb(parts[off], url))
    return crumbs


def gen_branches(oid):
    class Branch:
        def __init__(self, name, url):
            self.name = name
            self.url = url

    l = list(repo.branches.local)
    if oid not in l:
        l.append(oid)

    return [ Branch(name, "/view/" + name) for name in l ]


def view(request, oid, path):
    # First we normalize the path so libgit2 doesn't choke
    path = utils.normalize_path(path)

    # Find commit in the repo
    target = utils.find_branch_or_commit(repo, oid)
    if target is None:
        return HttpResponse("Invalid commit ID")

    # Resolve path inside commit
    obj = utils.resolve_path(target.tree, path)
    if obj == None:
        return HttpResponse("Invalid path")

    context = { "oid": oid,
                "path": path,
                "branches": gen_branches(oid),
                "crumbs": gen_crumbs(oid, path),
                }
    # Display correct template
    if obj.type == ObjectType.TREE:
        template = "tree.html"
        context["entries"] = utils.tree_entries(repo, target, obj, path)
    elif obj.type == ObjectType.BLOB:
        template, context["code"] = read_blob(obj)
    else:
        return HttpResponse("Unsupported object type")

    return render(request, template, context=context)
