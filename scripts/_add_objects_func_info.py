# TODO-barret; Add sentance in template to describe what the Relevant Function section is: "To learn more about details about the functions covered here, visit the reference links below."

import json
import subprocess
from typing import Union

import griffe.dataclasses as dc
import griffe.docstrings.dataclasses as ds
import griffe.expressions as exp
from griffe.collections import LinesCollection, ModulesCollection
from griffe.docstrings import Parser
from griffe.loader import GriffeLoader
from plum import dispatch
from quartodoc import MdRenderer, get_object, preview  # noqa: F401
from quartodoc.parsers import get_parser_defaults
from shiny import reactive, render, ui

loader = GriffeLoader(
    docstring_parser=Parser("numpy"),
    docstring_options=get_parser_defaults("numpy"),
    modules_collection=ModulesCollection(),
    lines_collection=LinesCollection(),
)


def fast_get_object(path: str):
    return get_object(path, loader=loader)


class FuncSignature(MdRenderer):
    style = "custom_func_signature"

    # def __init__(self, header_level: int = 1):
    #     self.header_level = header_level

    @dispatch
    def render(self, el):
        preview(el)
        print(el.annotation)
        raise NotImplementedError(f"Unsupported type: {type(el)}")

    @dispatch
    def render(self, el: str):
        return el

    @dispatch
    def render(self, el: Union[dc.Alias, dc.Object]):
        param_str = ""
        if hasattr(el, "docstring") and hasattr(el.docstring, "parsed"):
            for docstring_val in el.docstring.parsed:
                if isinstance(docstring_val, ds.DocstringSectionParameters):
                    param_str = self.render(docstring_val)
        elif hasattr(el, "parameters"):
            for param in el.parameters:
                param_str += self.render(param)
        return f"{el.name}({param_str})"

    @dispatch
    def render(self, el: None):
        return "None"

    @dispatch
    def render_annotation(self, el: str):
        return el

    @dispatch
    def render_annotation(
        self, el: Union[exp.ExprName, exp.ExprSubscript, exp.ExprBinOp]
    ):
        return el.path

    @dispatch
    def render(self, el: Union[ds.DocstringParameter, dc.Parameter]):
        param = self.render(el.name)
        annotation = self.render_annotation(el.annotation)
        if annotation:
            param = f"{param}: {annotation}"
        if el.default:
            param = f"{param} = {el.default}"
        return param

    @dispatch
    def render(self, el: ds.DocstringSectionParameters):
        return ", ".join(
            [item for item in map(self.render, el.value) if item is not None]
        )


def get_git_revision_short_hash() -> str:
    return (
        subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
        .decode("ascii")
        .strip()
    )


def get_git_current_tag() -> str:
    return (
        subprocess.check_output(["git", "tag", "--points-at", "HEAD"])
        .decode("ascii")
        .strip()
    )


class FuncFileLocation(MdRenderer):
    style = "custom_func_location"
    sha: str

    def __init__(self):
        sha = get_git_current_tag()
        if not sha:
            sha = get_git_revision_short_hash()
        self.sha = sha

    @dispatch
    def render(self, el):
        preview(el)
        raise NotImplementedError(f"Unsupported type: {type(el)}")

    @dispatch
    def render(self, el: Union[dc.Alias, dc.Object]):
        # preview(el)
        # import ipdb

        # ipdb.set_trace()

        rel_path = str(el.filepath).split("/shiny/")[-1]

        return {
            # "name": el.name,
            # "path": el.path,
            "github": f"https://github.com/posit-dev/py-shiny/blob/{self.sha}/shiny/{rel_path}#L{el.lineno}-L{el.endlineno}",
        }


# print(FuncSignature().render(fast_get_object("shiny:ui.input_action_button")))
# print(FuncSignature().render(fast_get_object("shiny:ui.input_action_button")))
# preview(fast_get_object("shiny:ui"))
# print("")

with open("objects.json") as infile:
    objects_content = json.load(infile)

# Collect rel links to functions
links = {}
for item in objects_content["items"]:
    if not item["name"].startswith("shiny."):
        continue
    name = item["name"].replace("shiny.", "")
    links[name] = item["uri"]
# preview(links)

fn_sig = FuncSignature()
file_locs = FuncFileLocation()
fn_info = {}
for mod_name, mod in [
    ("ui", ui),
    ("render", render),
    ("reactive", reactive),
]:
    print(f"## Collecting: {mod_name}")
    for key, f_obj in mod.__dict__.items():
        if key.startswith("_") or key in ("AnimationOptions",):
            continue
        if not callable(f_obj):
            continue
        # print(f"## {mod_name}.{key}")
        fn_obj = fast_get_object(f"shiny:{mod_name}.{key}")
        signature = f"{mod_name}.{fn_sig.render(fn_obj)}"
        name = f"{mod_name}.{key}"
        uri = None
        if name in links:
            uri = links[name]
        else:
            print(f"#### WARNING: No quartodoc entry/link found for {name}")
        fn_info[name] = {
            # "name": name,
            "uri": uri,
            "signature": signature,
            **file_locs.render(fn_obj),
        }
# preview(fn_info)

print("## Saving function information to objects.json")

objects_content["func_info"] = fn_info

# Serializing json
json_object = json.dumps(
    objects_content,
    # TODO-barret; remove
    indent=2,
)

# Writing to sample.json
with open("objects.json", "w") as outfile:
    outfile.write(json_object)
# TODO-barret; Include link to GitHub source
# print(FuncSignature().render(f_obj.annotation))
# print(preview(f_obj))

# # get annotation of first parameter
# obj.parameters[0].annotation

# render annotation
# print(renderer.render_annotation(obj.parameters[0].annotation))