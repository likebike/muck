## Lines like this one that begin with '##' are Mako comments.
##
## I NEED TO RE-DO THESE COMMENTS.  THEY ARE A BIT OUT-DATED.
##
## This template defines the site's visual structure.  You probably don't want to use this directly.
## Instead, you should probably inherit from it by using
## <%inherit file="./_base_pretty.mako"/> in another template.  You can then override
## whatever you want by using '<%def>' sections.
##
## Here is the Mako website and docs: http://www.makotemplates.org/
##
## Mini Mako Cheat Sheet:
##     ### Some Common Mako Syntax Structures ###
##     <%inherit file="..." />  --  Means that this template inherits from another template.
##     <%! ... %>  --  This is a "global" code block.  It gets run once when the template is loaded.
##     <% ... %>   --  This is a "normal" code block.  It gets run wherever it appears in the
##                     template.  So for example if it is in a loop, it will get run multiple times.
##     ${...}  --  Executes the enclosed expression and places the string output into the template.
##     %if ...: ... %endif
##     %for ...: ... %endfor
##     <%def name="ABC()">...</%def>   --  Defines a template function.  These can be overridden by
##                                         inheriting templates.  You usually evaluate these template
##                                         functions by using an ${self.ABC()} evaluation.
##     <%block name="XYZ">...</%block> --  Defines a template block, similar to a <%def> but more
##                                         convenient for inheritance of text, rather than functions.
##
##     ### Template Filenames ###
##     local.uri --  The FS path of *this* template, even if it is being called from an inheriting template.
##     self.uri  --  The FS path of the template that is actually being rendered.  It might be
##                   inheriting from the one that is currently running.
##
##     ### Inheritance stuff ###
##     self.body()  --  Refers to the 'body()' of the "end"  template in the inheritance chain.
##     next.body()  --  Refers to the 'body()' of the "next" template in the inheritance chain.
##
##     ### Using one template from another ###
##     <%include file="db.json.mako" />
##     ${context.lookup.get_template('db.json.mako').render_unicode().strip()}
##
##     ### PyHPy Provides the Following Convenience Features ###
##     self.URL('/blog.html')   --  Includes a "?_=${FS mtime}" in the URL.
##     self.URL()               --  Returns the project path of the template being rendered.
##                                  If /a/b/buildDir/x/y/z.mako is being rendered,
##                                  self.URL() --> /x/y/z.mako
##     self.FS_ROOT()           --  Returns the FS Path of the Build directory.
##     pyhpy.meta('/path/to/file.xyz')                  --  Returns metadata
##     <%block filter="pyhpy.markdown">...</%block>     --  Embed MarkDown
##
##
## This DOCTYPE specifies that our page is HTML 5:
<!DOCTYPE html>
## Use this trick to make life with IE easy:
<!--[if lt IE 7]>  <html class="no-js ie ie6 ie-lte9 ie-lte8 ie-lte7 ie-lte6" lang=en> <![endif]-->
<!--[if IE 7]>     <html class="no-js ie ie7 ie-lte9 ie-lte8 ie-lte7" lang=en> <![endif]-->
<!--[if IE 8]>     <html class="no-js ie ie8 ie-lte9 ie-lte8" lang=en> <![endif]-->
<!--[if IE 9]>     <html class="no-js ie ie9 ie-lte9" lang=en> <![endif]-->
<!--[if gt IE 9]>  <html class="no-js ie ie-gt9" lang=en> <![endif]-->
<!--[if !IE]><!--> <html class="no-js not-ie" lang=en> <!--<![endif]-->
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <link rel="shortcut icon" type="image/vnd.microsoft.icon" href="/favicon.ico">
    <title><%block name="TITLE">Muck</%block></title>
    <link rel="stylesheet" type="text/css" href="/static/lib/yui-3.12.0/reset_base_fonts-min.css">
    <link rel="stylesheet" type="text/css" href="/static/lib/font-awesome-4.5.0/css/font-awesome.css">
    <link rel="stylesheet" type="text/css" href="${pyhpy.url('/static/css/github-markdown.css')}">
    <link rel="stylesheet" type="text/css" href="${pyhpy.url('/static/css/base_pretty.css')}">
    <%block name="PAGE_CSS"></%block>
    <script type="text/javascript" src="/static/lib/jquery-1.10.2/jquery.js"></script>
    <script type="text/javascript" src="/static/lib/underscore-1.5.2/underscore.js"></script>
    <script type="text/javascript">
      ## Prevent the use of '$' because it is cryptic,
      ## and is easily confused with Mako template stuff.
      ## Use 'jQuery' instead.
      jQuery.noConflict();
    </script>
    %if self.debugPage():
      <script type="text/javascript" src="/static/lib/firebug-lite-1.3.2/build/firebug-lite.js">
        // You can use Ctrl+F12 or F12 to activate Firebug-lite.
        {
          startOpened:true,         // Make it obvious that we are in debug mode.
          showIconWhenHidden:false  // Don't screw with the elements on the page.
        }
      </script>
    %endif
    ## Un-comment for syntax highlighting:
    ##<link rel="stylesheet" type="text/css" href="/static/lib/highlightJS/styles/default.css">
    ##<script type="text/javascript" src="/static/lib/highlightJS/highlight.pack.js"></script>
    ##<script type="text/javascript">
    ##    hljs.initHighlightingOnLoad();
    ##</script>
    <script type="text/javascript" src="${pyhpy.url('/static/js/base_pretty.js')}"></script>
    <%block name="PAGE_JS"></%block>
  </head>
  <body>

    ## From http://tholman.com/github-corners/
    <a href="https://github.com/likebike/muck" class="github-corner" aria-label="View source on GitHub"><svg width="80" height="80" viewBox="0 0 250 250" style="fill:#151513; color:#fff; position: absolute; top: 0; border: 0; right: 0;" aria-hidden="true"><path d="M0,0 L115,115 L130,115 L142,142 L250,250 L250,0 Z"></path><path d="M128.3,109.0 C113.8,99.7 119.0,89.6 119.0,89.6 C122.0,82.7 120.5,78.6 120.5,78.6 C119.2,72.0 123.4,76.3 123.4,76.3 C127.3,80.9 125.5,87.3 125.5,87.3 C122.9,97.6 130.6,101.9 134.4,103.2" fill="currentColor" style="transform-origin: 130px 106px;" class="octo-arm"></path><path d="M115.0,115.0 C114.9,115.1 118.7,116.5 119.8,115.4 L133.7,101.6 C136.9,99.2 139.9,98.4 142.2,98.6 C133.8,88.0 127.5,74.4 143.8,58.0 C148.5,53.4 154.0,51.2 159.7,51.0 C160.3,49.4 163.2,43.6 171.4,40.1 C171.4,40.1 176.1,42.5 178.8,56.2 C183.1,58.6 187.2,61.8 190.9,65.4 C194.5,69.0 197.7,73.2 200.1,77.6 C213.8,80.2 216.3,84.9 216.3,84.9 C212.7,93.1 206.9,96.0 205.4,96.6 C205.1,102.4 203.0,107.8 198.3,112.5 C181.9,128.9 168.3,122.5 157.7,114.1 C157.9,116.9 156.7,120.9 152.7,124.9 L141.0,136.5 C139.8,137.7 141.6,141.9 141.8,141.8 Z" fill="currentColor" class="octo-body"></path></svg></a><style>.github-corner:hover .octo-arm{animation:octocat-wave 560ms ease-in-out}@keyframes octocat-wave{0%,100%{transform:rotate(0)}20%,60%{transform:rotate(-25deg)}40%,80%{transform:rotate(10deg)}}@media (max-width:500px){.github-corner:hover .octo-arm{animation:none}.github-corner .octo-arm{animation:octocat-wave 560ms ease-in-out}}</style>

    <section id=header>
      <a id=logo href="<%block name="LOGO_URL">${pyhpy.url('/index.html', mtime=None)}</%block>"><%block name="LOGO_IMAGE"><div class="asciiLogo vcompressed"><%text>
              .
          /\ /l
         ((.Y(!
          \ |/
          /  6~6,
          \ _    +-.
           \`-=--^-'
            \ \ 
           _/  \ 
          (  .  Y
         /"\ `--^--v--.
        / _ `--"T~\/~\/
       / " ~\.  !
 _    Y      Y./'
Y^|   |      |~~7
| l   |     / ./'
| `L  | Y .^/~T
|  l  ! | |/| |
| .`\/' | Y | !
 l "~   j l j_L______
  \,___{ __"~ __ ,\_,\_
</%text></div></%block> <%block name="LOGO_NAME"><div class=name>P<span class=y>y</span>HP<span class=y>y</span></div></%block></a>
      <%block name="LOGO_SLOGAN"><div id=slogan>makes you sound Austrylian</div></%block>
      ##<ul id=headerTabs>
      ##  <%block name="HEADER_TABS">
      ##  <li class=${'selected' if self.uri == '/index.html.mako' else 'unselected'}><a href="${pyhpy.url('/index.html', mtime=None)}"}><i class="fa fa-home"></i> Home</a></li>
      ##  <li class=${'selected' if self.uri.startswith('/photos') else 'unselected'}><a href="${pyhpy.url('/photos.html', mtime=None)}"}><i  class="fa fa-photo"></i> Photos</a></li>
      ##  <li class=${'selected' if self.uri.startswith('/blog') else 'unselected'}><a href="${pyhpy.url('/blog.html', mtime=None)}"}><i class="fa fa-newspaper-o"></i> Blog</a></li>
      ##  </%block>
      ##</ul>
      <div class=vspacer></div>
      <hr>
    </section>
    <section id=content>
      ## Render the inheriting template:
      ${next.body()}
    </section>
    <section id=footer>
      <hr>
      🄯 2016 <a href="http://likebike.com/">Christopher Sebastian</a>
    </section>
  </body>
</html>


## These are Mako '<%def>' sections.  They override values in the resulting templates.
## You can override these <%def>'s in templates that inherit from this one.
<%def name='debugPage()'><% return False %></%def>

<%! import pyhpy %>

## FOR FUTURE REFERENCE:
##
##   <link href='http://fonts.googleapis.com/css?family=Open+Sans' rel='stylesheet' type='text/css'>
## 
## 
## 
##   <!-- http://dev.w3.org/html5/markup/meta.name.html -->
##   <meta name="application-name" content="{{=request.application}}" />
## 
##
## 
## 
##   <!--  Mobile Viewport Fix
##         j.mp/mobileviewport & davidbcalhoun.com/2010/viewport-metatag
##         device-width: Occupy full width of the screen in its current orientation
##         initial-scale = 1.0 retains dimensions instead of zooming out if page height > device height
##         user-scalable = yes allows the user to zoom in -->
##   <meta name="viewport" content="width=device-width, initial-scale=1.0" />
## 
## 
##
## 
##   <link rel="apple-touch-icon" href="{{=self.URL('static','img/favicon.png')}}">
## 
##
## 
## 
##   <noscript>
##     <div id="nojs">
##       Please enable JavaScript to view this page properly.
##     </div>
##   </noscript>

