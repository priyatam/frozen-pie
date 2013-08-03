#!/usr/bin/env python
"""
Usage:
./bake.py

To serve in gh-pages
./bake.py serve

Algo:
Read config.yaml. For each post.md, process YAML, and apply its Mustache-HAML Template, and generate final HTML.
Lastly, combine everything into a single index.html with a minified CSS, JS.
"""

import sys
import time
from datetime import datetime
from importlib import import_module
import json
import os
import re
import yaml
import markdown as md
import pystache
from hamlpy import hamlpy
from scss import Scss
import coffeescript
import cssmin
import jsmin
import argparse
from subprocess import Popen, PIPE


### API ###

def load_config(config_path):
    """Loads configuration from config.yaml"""
    with open(config_path, "r") as fin:
        return yaml.load(fin.read())


def load_contents(config):
    """Creates a dictionary of Post meta data, including body as 'raw content'"""
    contents = []
    for fname in os.listdir(config['content']):
        if fname.endswith('.md') or fname.endswith('.txt'):
            try:
                yaml_data, raw_data = _read_yaml(config['content'], fname)
                fname = config['content'] + os.sep + fname
                content = {
                    "name": fname,
                    "body": raw_data, # unprocessed
                    "modified_date": _format_date(fname)
                }           
                content.update(yaml_data)  # Merge Yaml data for future lookup
                contents.append(content)
            except:
                print "Error occured reading file: %s, " % fname               
        else:
            print "Warning: Filename %s not in format: ['a/A', 2.5, '_', '.', '-', '~']" % fname
 
    return contents


def load_assets(config):
    """Loads assets as raw content into a dictionary, looked up by its fname.
    Closure accepts an asset ('templates', 'styles', 'posts', 'scripts') and a filter that filters based on file ext"""
    return lambda asset, filter: {fname: _read(fname, asset) for fname in os.listdir(asset) if fname.endswith(filter)}


def load_lambdas(config):
    """Loads all pure functions from each module under 'lambdas' as a dictionary lookup by funcion name"""
    modules = [import_module(config['lambdas'] + "." + recipe) for recipe in _get_lambdas(config)]
    return {funcname: getattr(mod, funcname) for mod in modules for funcname in dir(mod) if not funcname.startswith("__")}


def compile_assets(config, asset_type):
    """Closure: Compiles asset types: css, js, html using pre-processors"""
    def _compile(__compile, _from, _to, ):
        outputs = []
        for fname in os.listdir(config[asset_type]):
            if fname.endswith(_from):
                raw_data = __compile(asset_type,  fname)
                # Avoid including the output twice. Hint bake, by adding a _ filename convention
                new_filename = "_" + fname.replace(_from, _to)
                open(asset_type + os.sep + new_filename, 'w').write(raw_data)
                outputs.append((raw_data, new_filename))
        return outputs
    return _compile


def load_recipes(config):
    """Pre-process and load each asset type into a dict and return as a single recipe package: a tuple of dicts"""

    # Compile HAML
    _haml = {fname: compiled_out for compiled_out, fname in compile_assets(config, 'templates')(_compile_haml, 'haml', 'html')}
    _html = load_assets(config)('templates', 'html')
    templates = __newdict(_html, _haml)

    # Compile SCSS
    _scss = {fname: compiled_out for compiled_out, fname in compile_assets(config, 'styles')(_compile_scss, 'scss', 'css')}
    _css = load_assets(config)('styles', 'css')
    styles = __newdict(_css, _scss)

    # Compile Coffeescript
    _cs = {fname: compiled_out for compiled_out, fname in compile_assets(config, 'scripts')(_compile_coffee, 'coffee', 'js')}
    _js = load_assets(config)('scripts', 'js')
    scripts = __newdict(_js, _cs)

    # Load 3rd party logic
    lambdas = load_lambdas(config)
    
    return templates, styles, scripts, lambdas


def bake(config, templates, contents, styles, scripts, lambdas, minify=False):
    """Parse everything. Wrap results in a single page of html, css, js
       NOTE: This function modifies 'contents' by adding a new contents['html'] element"""

    # Content
    processor = {".txt": _textstache, ".md": _markstache }        
    for content in contents:
        try:
            for ext in processor.keys():
                if content['name'].endswith(ext):
                    _tmpl = content.get('template', config['default_template']) # set default if no template assigned
                    content['html'] = processor[ext](config, content, _get_template(_tmpl, templates), lambdas)
        except RuntimeError as e:
            print "Error baking content: %s %s" % content, e
            
    _params = {"relative_path": config['relative_path'],
               "title": config['title'],
               "posts": contents }

    # Scripts & Styles
    if minify:
        _params.update({"style_sheet": cssmin.cssmin("".join(styles.values())),
                        "script": jsmin.jsmin("".join(scripts.values())) })
    else:
        _params.update({"style_sheet": "".join(styles.values()),
                        "script": "".join(scripts.values()) })
        
    #Lambdas        
    _params.update(lambdas)
    
    # Json Data
    _params.update({"config": config})
    _params.update({"json_data": json.dumps(contents)})
    
    return pystache.render(templates['index.mustache.html'], _params)


def serve(config, version=None):
    """ Algo:
        create or replace deploy
        clone gh-pages into deploy
        git commit index.html -m "hash" (deploy/index.html can always be recreated from src hash)
        git push gh-pages """
    # Validate
    __config_path = "config.github.yaml"
    try:
        with open(__config_path): pass
    except IOError:
        print 'You need a config.github.yaml for serve.'
        exit(1)
        
    # Currently supports github
    _serve_github(config)


### SPI ###

def _get_template(template, templates):
    """Gets compiled html templates"""
    return templates[template] if template.endswith(".html") else templates["_" + template.replace(".haml", ".html")] 


def _read(fname, subdir):
    """Reads subdir/fname as raw content"""
    with open(subdir + os.sep + fname, "r") as fin:
        return fin.read()


def _read_yaml(subdir, fname):
    """Splits subdir/fname into a tuple of YAML and raw content"""
    with open(subdir + os.sep + fname, "r") as fin:
        yaml_and_raw = fin.read().split('\n---\n')
        if len(yaml_and_raw) == 1:
            return {}, yaml_and_raw[0]
        else:
            return yaml.load(yaml_and_raw[0]), yaml_and_raw[1]

def _serve_github(config):
    """TODO: Refactor this from brute force to git api"""
    proc = Popen(['git','config', "--get","remote.origin.url"],stdout=PIPE)
    url = proc.stdout.readline().rstrip("\n")
    os.system("rm -rf build")
    os.system("git clone -b gh-pages " + url + " build")
    os.system("cp deploy/index.html build/")
    os.system("cd build; git add index.html; git commit -m 'new deploy " + datetime.now() + "'; git push --force origin gh-pages")
    

def _markstache(config, post, template, lambdas=None):
    """Converts Markdown/Mustache/YAML to HTML."""
    html_md = md.markdown(post['body'].decode("utf-8"))
    _params = __newdict(post, {'body': html_md})
    _params.update(lambdas) if lambdas else None
    return pystache.render(template, _params)


def _textstache(config, content, template, lambdas=None):
    """Converts Markdown/Mustache/YAML to HTML."""
    txt = content['body'].decode("utf-8")
    _params = __newdict(content, {'body': txt})
    _params.update(lambdas) if lambdas else None
    return pystache.render(template, _params)

    
def _compile_haml(asset_type, fname):
    return hamlpy.Compiler().process(_read(fname, asset_type))


def _compile_scss(asset_type, fname):
    return Scss().compile(_read(fname, asset_type))


def _compile_coffee(asset_type, fname):
    return coffeescript.compile(_read(fname, asset_type))


def _format_date(fname):
    return datetime.strptime(time.ctime(os.path.getmtime(fname)), "%a %b %d %H:%M:%S %Y").strftime("%m-%d-%y")


def _get_lambdas(config):
    return [f.strip('.py') for f in os.listdir(config['lambdas']) if f.endswith('py') and not f.startswith("__")]


def _funcname(str):
    """To avoud namespace collisions, filename is a prefix to all functions defined in it. Ex: default_hello_world """
    return str.__name__.strip("lambdas.") + "_" + str


def __newdict(*dicts):
    _dict = {}
    for d in dicts:
        _dict.update(d)
    return _dict


### MAIN ###

def main(config_path, to_serve=False):
    """Let's cook an Apple Pie"""
    config = load_config(config_path)
    contents = load_contents(config)
    templates, styles, scripts, lambdas = load_recipes(config)
    
    pie = bake(config, templates, contents, styles, scripts, lambdas, minify=to_serve)
    open('deploy/index.html', 'w').write(pie)
    print 'Generated index.html'
    
    if to_serve:
        serve(config)


if __name__ == '__main__':
    # Parse commmand line options
    parser = argparse.ArgumentParser(description='Some options.')
    parser.add_argument('string_options', type=str, nargs="*", default=[])
    parser.add_argument("--config", nargs=1, default=["config.yaml"])
    args = parser.parse_args(sys.argv[1:])
    __config_path = args.config[0]
    to_serve = False
    if "serve" in args.string_options:
        to_serve = True        
    print "Using config from " + __config_path
    main(__config_path, to_serve=to_serve)