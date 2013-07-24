# Frozen Pie
        
> You know you have reached perfection in design, not when there is nothing more to add, but when 
there is nothing more to be taken away - Antoine de Saint-Exupery


Today's static site generators require css, markup, templating and programming skills. Their compatibility is broken. A template in one framework doesn't work in the other. You can't convert from LESS to Bourbon, from HTML to HAML, from Ruby closure to a Python inner function. You can't use Clojure's immutable collections to reimplement a default Mustache _loop_ in a straight forward way. You test on browsers, they break, like plugins that blow on your face. 
 
These toolkits are built for a different web, for a different generation. It requires a lot of work to perform simple tasks, like editing content, scrolling through posts and pages, designing a custom layout and pipeline lambdas onto a designer-friendly page. Things shouldn’t be this way. 
    
Not in Python.
    
**Frozen Pie**
   
create_crust
> Create content (posts and pages) in Markdown
    
put_in_pan
> Put in a logic-less templates with HAML-Mustache
    
add_filling
> Add config data in any content or template with YAML 
    
bake_in_oven
> Compile everything into a single index.html, scripts and styles included
    
serve
> git push index.html :gh-pages
    
Soon: Recipes.
 
---
Under active development. Not usable until a stable release. License: GPLv3
    
