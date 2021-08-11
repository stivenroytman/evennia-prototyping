"""
The EvMenu is a full in-game menu system for Evennia.

To start the menu, just import the EvMenu class from this module.

Example usage:
::

    from evennia.utils.evmenu import EvMenu

    EvMenu(caller, menu_module_path,
         startnode="node1",
         cmdset_mergetype="Replace", cmdset_priority=1,
         auto_quit=True, cmd_on_exit="look", persistent=True)

Where `caller` is the Object to use the menu on - it will get a new
cmdset while using the Menu. The `menu_module_path` is the python path
to a python module containing function definitions. By adjusting the
keyword options of the Menu() initialization call you can start the
menu at different places in the menu definition file, adjust if the
menu command should overload the normal commands or not, etc.

The `persistent` keyword will make the menu survive a server reboot.
It is `False` by default. Note that if using persistent mode, every
node and callback in the menu must be possible to be *pickled*, this
excludes e.g. callables that are class methods or functions defined
dynamically or as part of another function. In non-persistent mode
no such restrictions exist.

The menu is defined in a module (this can be the same module as the
command definition too) with function definitions:
::

    def node1(caller):
        # (this is the start node if called like above)
        # code
        return text, options

    def node_with_other_name(caller, input_string):
        # code
        return text, options

    def another_node(caller, input_string, **kwargs):
        # code
        return text, options

Where `caller` is the object using the menu and input_string is the
command entered by the user on the *previous* node (the command
entered to get to this node). The node function code will only be
executed once per node-visit and the system will accept nodes with
both one or two arguments interchangeably. It also accepts nodes
that takes `**kwargs`.

The menu tree itself is available on the caller as
`caller.ndb._evmenu`. This makes it a convenient place to store
temporary state variables between nodes, since this NAttribute is
deleted when the menu is exited.

The return values must be given in the above order, but each can be
returned as None as well. If the options are returned as None, the
menu is immediately exited and the default "look" command is called.

- `text` (str, tuple or None): Text shown at this node. If a tuple, the
  second element in the tuple is a help text to display at this
  node when the user enters the menu help command there.
- `options` (tuple, dict or None): If `None`, this exits the menu.
  If a single dict, this is a single-option node. If a tuple,
  it should be a tuple of option dictionaries. Option dicts have
  the following keys:

  - `key` (str or tuple, optional): What to enter to choose this option.
      If a tuple, it must be a tuple of strings, where the first string is the
      key which will be shown to the user and the others are aliases.
      If unset, the options' number will be used. The special key `_default`
      marks this option as the default fallback when no other option matches
      the user input. There can only be one `_default` option per node. It
      will not be displayed in the list.
  - `desc` (str, optional): This describes what choosing the option will do.
  - `goto` (str, tuple or callable): If string, should be the name of node to go to
      when this option is selected. If a callable, it has the signature
      `callable(caller[,raw_input][,**kwargs])`. If a tuple, the first element
      is the callable and the second is a dict with the kwargs to pass to
      the callable. Those kwargs will also be passed into the next node if possible.
      Such a callable should return either a str or a (str, dict), where the
      string is the name of the next node to go to and the dict is the new,
      (possibly modified) kwarg to pass into the next node. If the callable returns
      None or the empty string, the current node will be revisited.
  - `exec` (str, callable or tuple, optional): This takes the same input as `goto` above
      and runs before it. If given a node name, the node will be executed but will not
      be considered the next node. If node/callback returns str or (str, dict), these will
      replace the `goto` step (`goto` callbacks will not fire), with the string being the
      next node name and the optional dict acting as the kwargs-input for the next node.
      If an exec callable returns `None`, the current node is re-run.

If key is not given, the option will automatically be identified by
its number 1..N.

Example:
::

    # in menu_module.py

    def node1(caller):
        text = ("This is a node text",
                "This is help text for this node")
        options = ({"key": "testing",
                    "desc": "Select this to go to node 2",
                    "goto": ("node2", {"foo": "bar"}),
                    "exec": "callback1"},
                   {"desc": "Go to node 3.",
                    "goto": "node3"})
        return text, options

    def callback1(caller):
        # this is called when choosing the "testing" option in node1
        # (before going to node2). If it returned a string, say 'node3',
        # then the next node would be node3 instead of node2 as specified
        # by the normal 'goto' option key above.
        caller.msg("Callback called!")

    def node2(caller, **kwargs):
        text = '''
            This is node 2. It only allows you to go back
            to the original node1. This extra indent will
            be stripped. We don't include a help text but
            here are the variables passed to us: {}
            '''.format(kwargs)
        options = {"goto": "node1"}
        return text, options

    def node3(caller):
        text = "This ends the menu since there are no options."
        return text, None

When starting this menu with  `Menu(caller, "path.to.menu_module")`,
the first node will look something like this:
::

    This is a node text
    ______________________________________

    testing: Select this to go to node 2
    2: Go to node 3

Where you can both enter "testing" and "1" to select the first option.
If the client supports MXP, they may also mouse-click on "testing" to
do the same. When making this selection, a function "callback1" in the
same Using `help` will show the help text, otherwise a list of
available commands while in menu mode.

The menu tree is exited either by using the in-menu quit command or by
reaching a node without any options.


For a menu demo, import CmdTestMenu from this module and add it to
your default cmdset. Run it with this module, like `testmenu
evennia.utils.evmenu`.


## Menu generation from template string

In evmenu.py is a helper function `parse_menu_template` that parses a
template-string and outputs a menu-tree dictionary suitable to pass into
EvMenu:
::

    menutree = evmenu.parse_menu_template(caller, menu_template, goto_callables)
    EvMenu(caller, menutree)

For maximum flexibility you can inject normally-created nodes in the menu tree
before passing it to EvMenu. If that's not needed, you can also create a menu
in one step with:
::

    evmenu.template2menu(caller, menu_template, goto_callables)

The `goto_callables` is a mapping `{"funcname": callable, ...}`, where each
callable must be a module-global function on the form
`funcname(caller, raw_string, **kwargs)` (like any goto-callable). The
`menu_template` is a multi-line string on the following form:
::

    ## node start

    This is the text of the start node.
    The text area can have multiple lines, line breaks etc.

    Each option below is one of these forms
        key: desc -> gotostr_or_func
        key: gotostr_or_func
        >: gotostr_or_func
        > glob/regex: gotostr_or_func

    ## options

        # comments are only allowed from beginning of line.
        # Indenting is not necessary, but good for readability

        1: Option number 1 -> node1
        2: Option number 2 -> node2
        next: This steps next -> go_back()
        # the -> can be ignored if there is no desc
        back: go_back(from_node=start)
        abort: abort

    ## node node1

    Text for Node1. Enter a message!
    <return> to go back.

    ## options

        # Starting the option-line with >
        # allows to perform different actions depending on
        # what is inserted.

        # this catches everything starting with foo
        > foo*: handle_foo_message()

        # regex are also allowed (this catches number inputs)
        > [0-9]+?: handle_numbers()

        # this catches the empty return
        >: start

        # this catches everything else
        > *: handle_message(from_node=node1)

    ## node node2

    Text for Node2. Just go back.

    ## options

        >: start

    # node abort

    This exits the menu since there is no `## options` section.

Each menu node is defined by a `# node <name>` containing the text of the node,
followed by `## options` Also `## NODE` and `## OPTIONS` work. No python code
logics is allowed in the template, this code is not evaluated but parsed. More
advanced dynamic usage requires a full node-function (which can be added to the
generated dict, as said).

Adding `(..)` to a goto treats it as a callable and it must then be included in
the `goto_callable` mapping. Only named keywords (or no args at all) are
allowed, these will be added to the `**kwargs` going into the callable. Quoting
strings is only needed if wanting to pass strippable spaces, otherwise the
key:values will be converted to strings/numbers with literal_eval before passed
into the callable.

The "> " option takes a glob or regex to perform different actions depending on user
input. Make sure to sort these in increasing order of generality since they
will be tested in sequence.

----

"""

import re
import inspect

from ast import literal_eval
from fnmatch import fnmatch

from inspect import isfunction, getargspec
from django.conf import settings
from evennia import Command, CmdSet
from evennia.utils import logger
from evennia.utils.evtable import EvTable
from evennia.utils.ansi import strip_ansi
from evennia.utils.utils import mod_import, make_iter, pad, to_str, m_len, is_iter, dedent, crop
from evennia.commands import cmdhandler

# i18n
from django.utils.translation import gettext as _

# read from protocol NAWS later?
_MAX_TEXT_WIDTH = settings.CLIENT_DEFAULT_WIDTH

# we use cmdhandler instead of evennia.syscmdkeys to
# avoid some cases of loading before evennia init'd
_CMD_NOMATCH = cmdhandler.CMD_NOMATCH
_CMD_NOINPUT = cmdhandler.CMD_NOINPUT

# Return messages


_ERR_NOT_IMPLEMENTED = _(
    "Menu node '{nodename}' is either not implemented or caused an error. "
    "Make another choice or try 'q' to abort."
)
_ERR_GENERAL = _("Error in menu node '{nodename}'.")
_ERR_NO_OPTION_DESC = _("No description.")
_HELP_FULL = _("Commands: <menu option>, help, quit")
_HELP_NO_QUIT = _("Commands: <menu option>, help")
_HELP_NO_OPTIONS = _("Commands: help, quit")
_HELP_NO_OPTIONS_NO_QUIT = _("Commands: help")
_HELP_NO_OPTION_MATCH = _("Choose an option or try 'help'.")

_ERROR_PERSISTENT_SAVING = """
{error}

|rThe menu state could not be saved for persistent mode. Switching
to non-persistent mode (which means the menu session won't survive
an eventual server reload).|n
"""

_TRACE_PERSISTENT_SAVING = (
    "EvMenu persistent-mode error. Commonly, this is because one or "
    "more of the EvEditor callbacks could not be pickled, for example "
    "because it's a class method or is defined inside another function."
)


class EvMenuError(RuntimeError):
    """
    Error raised by menu when facing internal errors.

    """

    pass


class EvMenuGotoAbortMessage(RuntimeError):
    """
    This can be raised by a goto-callable to abort the goto flow.  The message
    stored with the executable will be sent to the caller who will remain on
    the current node. This can be used to pass single-line returns without
    re-running the entire node with text and options.

    Example:
        raise EvMenuGotoMessage("That makes no sense.")

    """


# -------------------------------------------------------------
#
# Menu command and command set
#
# -------------------------------------------------------------


class CmdEvMenuNode(Command):
    """
    Menu options.
    """

    key = _CMD_NOINPUT
    aliases = [_CMD_NOMATCH]
    locks = "cmd:all()"
    help_category = "Menu"
    auto_help_display_key = "<menu commands>"

    def get_help(self):
        return "Menu commands are explained within the menu."

    def func(self):
        """
        Implement all menu commands.
        """

        def _restore(caller):
            # check if there is a saved menu available.
            # this will re-start a completely new evmenu call.
            saved_options = caller.attributes.get("_menutree_saved")
            if saved_options:
                startnode_tuple = caller.attributes.get("_menutree_saved_startnode")
                try:
                    startnode, startnode_input = startnode_tuple
                except ValueError:  # old form of startnode store
                    startnode, startnode_input = startnode_tuple, ""
                if startnode:
                    saved_options[2]["startnode"] = startnode
                    saved_options[2]["startnode_input"] = startnode_input
                MenuClass = saved_options[0]
                # this will create a completely new menu call
                MenuClass(caller, *saved_options[1], **saved_options[2])
                return True
            return None

        caller = self.caller
        # we store Session on the menu since this can be hard to
        # get in multisession environemtns if caller is an Account.
        menu = caller.ndb._evmenu
        if not menu:
            if _restore(caller):
                return
            orig_caller = caller
            caller = caller.account if hasattr(caller, "account") else None
            menu = caller.ndb._evmenu if caller else None
            if not menu:
                if caller and _restore(caller):
                    return
                caller = self.session
                menu = caller.ndb._evmenu
                if not menu:
                    # can't restore from a session
                    err = "Menu object not found as %s.ndb._evmenu!" % orig_caller
                    orig_caller.msg(
                        err
                    )  # don't give the session as a kwarg here, direct to original
                    raise EvMenuError(err)
        # we must do this after the caller with the menu has been correctly identified since it
        # can be either Account, Object or Session (in the latter case this info will be superfluous).
        caller.ndb._evmenu._session = self.session
        # we have a menu, use it.
        menu.parse_input(self.raw_string)


class EvMenuCmdSet(CmdSet):
    """
    The Menu cmdset replaces the current cmdset.

    """

    key = "menu_cmdset"
    priority = 1
    mergetype = "Replace"
    no_objs = True
    no_exits = True
    no_channels = False

    def at_cmdset_creation(self):
        """
        Called when creating the set.
        """
        self.add(CmdEvMenuNode())


# ------------------------------------------------------------
#
# Menu main class
#
# -------------------------------------------------------------


class EvMenu:
    """
    This object represents an operational menu. It is initialized from
    a menufile.py instruction.

    """

    # convenient helpers for easy overloading
    node_border_char = "_"

    def __init__(
        self,
        caller,
        menudata,
        startnode="start",
        cmdset_mergetype="Replace",
        cmdset_priority=1,
        auto_quit=True,
        auto_look=True,
        auto_help=True,
        cmd_on_exit="look",
        persistent=False,
        startnode_input="",
        session=None,
        debug=False,
        **kwargs,
    ):
        """
        Initialize the menu tree and start the caller onto the first node.

        Args:
            caller (Object, Account or Session): The user of the menu.
            menudata (str, module or dict): The full or relative path to the module
                holding the menu tree data. All global functions in this module
                whose name doesn't start with '_ ' will be parsed as menu nodes.
                Also the module itself is accepted as input. Finally, a dictionary
                menu tree can be given directly. This must then be a mapping
                `{"nodekey":callable,...}` where `callable` must be called as
                and return the data expected of a menu node. This allows for
                dynamic menu creation.
            startnode (str, optional): The starting node name in the menufile.
            cmdset_mergetype (str, optional): 'Replace' (default) means the menu
                commands will be exclusive - no other normal commands will
                be usable while the user is in the menu. 'Union' means the
                menu commands will be integrated with the existing commands
                (it will merge with `merge_priority`), if so, make sure that
                the menu's command names don't collide with existing commands
                in an unexpected way. Also the CMD_NOMATCH and CMD_NOINPUT will
                be overloaded by the menu cmdset. Other cmdser mergetypes
                has little purpose for the menu.
            cmdset_priority (int, optional): The merge priority for the
                menu command set. The default (1) is usually enough for most
                types of menus.
            auto_quit (bool, optional): Allow user to use "q", "quit" or
                "exit" to leave the menu at any point. Recommended during
                development!
            auto_look (bool, optional): Automatically make "looK" or "l" to
                re-show the last node. Turning this off means you have to handle
                re-showing nodes yourself, but may be useful if you need to
                use "l" for some other purpose.
            auto_help (bool, optional): Automatically make "help" or "h" show
                the current help entry for the node. If turned off, eventual
                help must be handled manually, but it may be useful if you
                need 'h' for some other purpose, for example.
            cmd_on_exit (callable, str or None, optional): When exiting the menu
                (either by reaching a node with no options or by using the
                in-built quit command (activated with `allow_quit`), this
                callback function or command string will be executed.
                The callback function takes two parameters, the caller then the
                EvMenu object. This is called after cleanup is complete.
                Set to None to not call any command.
            persistent (bool, optional): Make the Menu persistent (i.e. it will
                survive a reload. This will make the Menu cmdset persistent. Use
                with caution - if your menu is buggy you may end up in a state
                you can't get out of! Also note that persistent mode requires
                that all formatters, menu nodes and callables are possible to
                *pickle*. When the server is reloaded, the latest node shown will be completely
                re-run with the same input arguments - so be careful if you are counting
                up some persistent counter or similar - the counter may be run twice if
                reload happens on the node that does that. Note that if `debug` is True,
                this setting is ignored and assumed to be False.
            startnode_input (str or (str, dict), optional): Send an input text to `startnode` as if
                a user input text from a fictional previous node. If including the dict, this will
                be passed as **kwargs to that node. When the server reloads,
                the latest visited node will be re-run as `node(caller, raw_string, **kwargs)`.
            session (Session, optional): This is useful when calling EvMenu from an account
                in multisession mode > 2. Note that this session only really relevant
                for the very first display of the first node - after that, EvMenu itself
                will keep the session updated from the command input. So a persistent
                menu will *not* be using this same session anymore after a reload.
            debug (bool, optional): If set, the 'menudebug' command will be made available
                by default in all nodes of the menu. This will print out the current state of
                the menu. Deactivate for production use! When the debug flag is active, the
                `persistent` flag is deactivated.

        Keyword Args:
            any (any): All kwargs will become initialization variables on `caller.ndb._evmenu`,
                to be available at run.

        Raises:
            EvMenuError: If the start/end node is not found in menu tree.

        Notes:
            While running, the menu is stored on the caller as `caller.ndb._evmenu`. Also
            the current Session (from the Command, so this is still valid in multisession
            environments) is available through `caller.ndb._evmenu._session`. The `_evmenu`
            property is a good one for storing intermediary data on between nodes since it
            will be automatically deleted when the menu closes.

            In persistent mode, all nodes, formatters and callbacks in the menu must be
            possible to be *pickled*, this excludes e.g. callables that are class methods
            or functions defined dynamically or as part of another function. In
            non-persistent mode no such restrictions exist.

        """
        self._startnode = startnode
        self._menutree = self._parse_menudata(menudata)
        self._persistent = persistent if not debug else False
        self._quitting = False

        if startnode not in self._menutree:
            raise EvMenuError("Start node '%s' not in menu tree!" % startnode)

        # public variables made available to the command

        self.caller = caller

        # track EvMenu kwargs
        self.auto_quit = auto_quit
        self.auto_look = auto_look
        self.auto_help = auto_help
        self.debug_mode = debug
        self._session = session
        if isinstance(cmd_on_exit, str):
            # At this point menu._session will have been replaced by the
            # menu command to the actual session calling.
            self.cmd_on_exit = lambda caller, menu: caller.execute_cmd(
                cmd_on_exit, session=menu._session
            )
        elif callable(cmd_on_exit):
            self.cmd_on_exit = cmd_on_exit
        else:
            self.cmd_on_exit = None
        # current menu state
        self.default = None
        self.nodetext = None
        self.helptext = None
        self.options = None
        self.nodename = None
        self.node_kwargs = {}

        # used for testing
        self.test_options = {}
        self.test_nodetext = ""

        # assign kwargs as initialization vars on ourselves.
        reserved_clash = set(
            (
                "_startnode",
                "_menutree",
                "_session",
                "_persistent",
                "cmd_on_exit",
                "default",
                "nodetext",
                "helptext",
                "options",
                "cmdset_mergetype",
                "auto_quit",
            )
        ).intersection(set(kwargs.keys()))
        if reserved_clash:
            raise RuntimeError(
                f"One or more of the EvMenu `**kwargs` ({list(reserved_clash)}) is reserved by EvMenu for internal use."
            )
        for key, val in kwargs.items():
            setattr(self, key, val)

        if self.caller.ndb._evmenu:
            # an evmenu already exists - we try to close it cleanly. Note that this will
            # not fire the previous menu's end node.
            try:
                self.caller.ndb._evmenu.close_menu()
            except Exception:
                pass

        # store ourself on the object
        self.caller.ndb._evmenu = self

        # DEPRECATED - for backwards-compatibility
        self.caller.ndb._menutree = self

        if persistent:
            # save the menu to the database
            calldict = {
                "startnode": startnode,
                "cmdset_mergetype": cmdset_mergetype,
                "cmdset_priority": cmdset_priority,
                "auto_quit": auto_quit,
                "auto_look": auto_look,
                "auto_help": auto_help,
                "cmd_on_exit": cmd_on_exit,
                "persistent": persistent,
            }
            calldict.update(kwargs)
            try:
                caller.attributes.add("_menutree_saved", (self.__class__, (menudata,), calldict))
                caller.attributes.add("_menutree_saved_startnode", (startnode, startnode_input))
            except Exception as err:
                self.msg(_ERROR_PERSISTENT_SAVING.format(error=err))
                logger.log_trace(_TRACE_PERSISTENT_SAVING)
                persistent = False

        # set up the menu command on the caller
        menu_cmdset = EvMenuCmdSet()
        menu_cmdset.mergetype = str(cmdset_mergetype).lower().capitalize() or "Replace"
        menu_cmdset.priority = int(cmdset_priority)
        self.caller.cmdset.add(menu_cmdset, permanent=persistent)

        reserved_startnode_kwargs = set(("nodename", "raw_string"))
        startnode_kwargs = {}
        if isinstance(startnode_input, (tuple, list)) and len(startnode_input) > 1:
            startnode_input, startnode_kwargs = startnode_input[:2]
            if not isinstance(startnode_kwargs, dict):
                raise EvMenuError("startnode_input must be either a str or a tuple (str, dict).")
            clashing_kwargs = reserved_startnode_kwargs.intersection(set(startnode_kwargs.keys()))
            if clashing_kwargs:
                raise RuntimeError(
                    f"Evmenu startnode_inputs includes kwargs {tuple(clashing_kwargs)} that "
                    "clashes with EvMenu's internal usage."
                )

        # start the menu
        self.goto(self._startnode, startnode_input, **startnode_kwargs)

    def _parse_menudata(self, menudata):
        """
        Parse a menufile for node functions and store in dictionary
        map. Alternatively, accept a pre-made mapping dictionary of
        node functions.

        Args:
            menudata (str, module or dict): The python.path to the menufile,
                or the python module itself. If a dict, this should be a
                mapping nodename:callable, where the callable must match
                the criteria for a menu node.

        Returns:
            menutree (dict): A {nodekey: func}

        """
        if isinstance(menudata, dict):
            # This is assumed to be a pre-loaded menu tree.
            return menudata
        else:
            # a python path of a module
            module = mod_import(menudata)
            return dict(
                (key, func)
                for key, func in module.__dict__.items()
                if isfunction(func) and not key.startswith("_")
            )

    def _format_node(self, nodetext, optionlist):
        """
        Format the node text + option section

        Args:
            nodetext (str): The node text
            optionlist (list): List of (key, desc) pairs.

        Returns:
            string (str): The options section, including
                all needed spaces.

        Notes:
            This will adjust the columns of the options, first to use
            a maxiumum of 4 rows (expanding in columns), then gradually
            growing to make use of the screen space.

        """

        # handle the node text
        nodetext = self.nodetext_formatter(nodetext)

        # handle the options
        optionstext = self.options_formatter(optionlist)

        # format the entire node
        return self.node_formatter(nodetext, optionstext)

    def _safe_call(self, callback, raw_string, **kwargs):
        """
        Call a node-like callable, with a variable number of raw_string, *args, **kwargs, all of
        which should work also if not present (only `caller` is always required). Return its result.

        Viable node-like callable forms:
        ::

            _callname(caller)
            _callname(caller, raw_string)
            _callname(caller, **kwargs)
            _callname(caller, raw_string, **kwargs)

        If this is a node:

        - `caller` is the one using the menu.
        - `raw_string` is the users exact input on the *previous* node.
        - `**kwargs` is either passed through the previous node or returned
          along with the node name from the goto-callable leading to this node.

        If this is a goto-callable:

        - `caller` is the one using the menu.
        - `raw_string` is the user's exact input when chosing the option that triggered
          this goto-callable.
        - `**kwargs` is any extra dict passed to the callable in the option
          definition, or (if no explit kwarg was given to the callable) the
          previous node's kwarg, if any.

        """
        try:
            try:
                nargs = len(getargspec(callback).args)
            except TypeError:
                raise EvMenuError("Callable {} doesn't accept any arguments!".format(callback))
            supports_kwargs = bool(getargspec(callback).keywords)
            if nargs <= 0:
                raise EvMenuError("Callable {} doesn't accept any arguments!".format(callback))

            if supports_kwargs:
                if nargs > 1:
                    ret = callback(self.caller, raw_string, **kwargs)
                    # callback accepting raw_string, **kwargs
                else:
                    # callback accepting **kwargs
                    ret = callback(self.caller, **kwargs)
            elif nargs > 1:
                # callback accepting raw_string
                ret = callback(self.caller, raw_string)
            else:
                # normal callback, only the caller as arg
                ret = callback(self.caller)
        except EvMenuError:
            errmsg = _ERR_GENERAL.format(nodename=callback)
            self.msg(errmsg)
            logger.log_trace()
            raise

        return ret

    def _execute_node(self, nodename, raw_string, **kwargs):
        """
        Execute a node.

        Args:
            nodename (str): Name of node.
            raw_string (str): The raw default string entered on the
                previous node (only used if the node accepts it as an
                argument)
            kwargs (any, optional): Optional kwargs for the node.

        Returns:
            nodetext, options (tuple): The node text (a string or a
                tuple and the options tuple, if any.

        """
        try:
            node = self._menutree[nodename]
        except KeyError:
            self.msg(_ERR_NOT_IMPLEMENTED.format(nodename=nodename))
            raise EvMenuError
        try:
            kwargs["_current_nodename"] = nodename
            ret = self._safe_call(node, raw_string, **kwargs)
            if isinstance(ret, (tuple, list)) and len(ret) > 1:
                nodetext, options = ret[:2]
            else:
                nodetext, options = ret, None
        except KeyError:
            self.msg(_ERR_NOT_IMPLEMENTED.format(nodename=nodename))
            logger.log_trace()
            raise EvMenuError
        except Exception:
            self.msg(_ERR_GENERAL.format(nodename=nodename))
            logger.log_trace()
            raise

        # store options to make them easier to test
        self.test_options = options
        self.test_nodetext = nodetext

        return nodetext, options

    def msg(self, txt):
        """
        This is a central point for sending return texts to the caller. It
        allows for a central point to add custom messaging when creating custom
        EvMenu overrides.

        Args:
            txt (str): The text to send.

        Notes:
            By default this will send to the same session provided to EvMenu
            (if `session` kwarg was provided to `EvMenu.__init__`). It will
            also send it with a `type=menu` for the benefit of OOB/webclient.

        """
        self.caller.msg(text=(txt, {"type": "menu"}), session=self._session)

    def run_exec(self, nodename, raw_string, **kwargs):
        """
        NOTE: This is deprecated. Use `goto` directly instead.

        Run a function or node as a callback (with the 'exec' option key).

        Args:
            nodename (callable or str): A callable to run as
                `callable(caller, raw_string)`, or the Name of an existing
                node to run as a callable. This may or may not return
                a string.
            raw_string (str): The raw default string entered on the
                previous node (only used if the node accepts it as an
                argument)
            kwargs (any): These are optional kwargs passed into goto

        Returns:
            new_goto (str or None): A replacement goto location string or
                None (no replacement).
        Notes:
            Relying on exec callbacks to set the goto location is
            very powerful but will easily lead to spaghetti structure and
            hard-to-trace paths through the menu logic. So be careful with
            relying on this.

        """
        try:
            if callable(nodename):
                # this is a direct callable - execute it directly
                ret = self._safe_call(nodename, raw_string, **kwargs)
                if isinstance(ret, (tuple, list)):
                    if not len(ret) > 1 or not isinstance(ret[1], dict):
                        raise EvMenuError(
                            "exec callable must return either None, str or (str, dict)"
                        )
                    ret, kwargs = ret[:2]
            else:
                # nodename is a string; lookup as node and run as node in-place (don't goto it)
                # execute the node
                ret = self._execute_node(nodename, raw_string, **kwargs)
                if isinstance(ret, (tuple, list)):
                    if not len(ret) > 1 and ret[1] and not isinstance(ret[1], dict):
                        raise EvMenuError("exec node must return either None, str or (str, dict)")
                    ret, kwargs = ret[:2]
        except EvMenuError as err:
            errmsg = "Error in exec '%s' (input: '%s'): %s" % (nodename, raw_string.rstrip(), err)
            self.msg("|r%s|n" % errmsg)
            logger.log_trace(errmsg)
            return

        if isinstance(ret, str):
            # only return a value if a string (a goto target), ignore all other returns
            if not ret:
                # an empty string - rerun the same node
                return self.nodename
            return ret, kwargs
        return None

    def extract_goto_exec(self, nodename, option_dict):
        """
        Helper: Get callables and their eventual kwargs.

        Args:
            nodename (str): The current node name (used for error reporting).
            option_dict (dict): The seleted option's dict.

        Returns:
            goto (str, callable or None): The goto directive in the option.
            goto_kwargs (dict): Kwargs for `goto` if the former is callable, otherwise empty.
            execute (callable or None): Executable given by the `exec` directive.
            exec_kwargs (dict): Kwargs for `execute` if it's callable, otherwise empty.

        """
        goto_kwargs, exec_kwargs = {}, {}
        goto, execute = option_dict.get("goto", None), option_dict.get("exec", None)
        if goto and isinstance(goto, (tuple, list)):
            if len(goto) > 1:
                goto, goto_kwargs = goto[:2]  # ignore any extra arguments
                if not hasattr(goto_kwargs, "__getitem__"):
                    #  not a dict-like structure
                    raise EvMenuError(
                        "EvMenu node {}: goto kwargs is not a dict: {}".format(
                            nodename, goto_kwargs
                        )
                    )
            else:
                goto = goto[0]
        if execute and isinstance(execute, (tuple, list)):
            if len(execute) > 1:
                execute, exec_kwargs = execute[:2]  # ignore any extra arguments
                if not hasattr(exec_kwargs, "__getitem__"):
                    #  not a dict-like structure
                    raise EvMenuError(
                        "EvMenu node {}: exec kwargs is not a dict: {}".format(
                            nodename, goto_kwargs
                        )
                    )
            else:
                execute = execute[0]
        return goto, goto_kwargs, execute, exec_kwargs

    def goto(self, nodename, raw_string, **kwargs):
        """
        Run a node by name, optionally dynamically generating that name first.

        Args:
            nodename (str or callable): Name of node or a callable
                to be called as `function(caller, raw_string, **kwargs)` or
                `function(caller, **kwargs)` to return the actual goto string or
                a ("nodename", kwargs) tuple.
            raw_string (str): The raw default string entered on the
                previous node (only used if the node accepts it as an
                argument)
        Keyword Args:
            any: Extra arguments to goto callables.

        """

        if callable(nodename):
            # run the "goto" callable, if possible
            inp_nodename = nodename
            nodename = self._safe_call(nodename, raw_string, **kwargs)
            if isinstance(nodename, (tuple, list)):
                if not len(nodename) > 1 or not isinstance(nodename[1], dict):
                    raise EvMenuError(
                        "{}: goto callable must return str or (str, dict)".format(inp_nodename)
                    )
                nodename, kwargs = nodename[:2]
            if not nodename:
                # no nodename return. Re-run current node
                nodename = self.nodename
        try:
            # execute the found node, make use of the returns.
            nodetext, options = self._execute_node(nodename, raw_string, **kwargs)
        except EvMenuError:
            return

        if self._persistent:
            self.caller.attributes.add(
                "_menutree_saved_startnode", (nodename, (raw_string, kwargs))
            )

        # validation of the node return values
        helptext = ""
        if is_iter(nodetext):
            if len(nodetext) > 1:
                nodetext, helptext = nodetext[:2]
            else:
                nodetext = nodetext[0]
        nodetext = "" if nodetext is None else str(nodetext)
        options = [options] if isinstance(options, dict) else options

        # this will be displayed in the given order
        display_options = []
        # this is used for lookup
        self.options = {}
        self.default = None
        if options:
            for inum, dic in enumerate(options):
                # fix up the option dicts
                keys = make_iter(dic.get("key"))
                desc = dic.get("desc", dic.get("text", None))
                if "_default" in keys:
                    keys = [key for key in keys if key != "_default"]
                    goto, goto_kwargs, execute, exec_kwargs = self.extract_goto_exec(nodename, dic)
                    self.default = (goto, goto_kwargs, execute, exec_kwargs)
                else:
                    # use the key (only) if set, otherwise use the running number
                    keys = list(make_iter(dic.get("key", str(inum + 1).strip())))
                    goto, goto_kwargs, execute, exec_kwargs = self.extract_goto_exec(nodename, dic)
                if keys:
                    display_options.append((keys[0], desc))
                    for key in keys:
                        if goto or execute:
                            self.options[strip_ansi(key).strip().lower()] = (
                                goto,
                                goto_kwargs,
                                execute,
                                exec_kwargs,
                            )

        self.nodetext = self._format_node(nodetext, display_options)
        self.node_kwargs = kwargs
        self.nodename = nodename

        # handle the helptext
        if helptext:
            self.helptext = self.helptext_formatter(helptext)
        elif options:
            self.helptext = _HELP_FULL if self.auto_quit else _HELP_NO_QUIT
        else:
            self.helptext = _HELP_NO_OPTIONS if self.auto_quit else _HELP_NO_OPTIONS_NO_QUIT

        self.display_nodetext()
        if not options:
            self.close_menu()

    def run_exec_then_goto(self, runexec, goto, raw_string, runexec_kwargs=None, goto_kwargs=None):
        """
        Call 'exec' callback and goto (which may also be a callable) in sequence.

        Args:
            runexec (callable or str): Callback to run before goto. If
                the callback returns a string, this is used to replace
                the `goto` string/callable before being passed into the goto handler.
            goto (str): The target node to go to next (may be replaced
                by `runexec`)..
            raw_string (str): The original user input.
            runexec_kwargs (dict, optional): Optional kwargs for runexec.
            goto_kwargs (dict, optional): Optional kwargs for goto.

        """
        if runexec:
            # replace goto only if callback returns
            goto, goto_kwargs = self.run_exec(
                runexec, raw_string, **(runexec_kwargs if runexec_kwargs else {})
            ) or (goto, goto_kwargs)
        if goto:
            self.goto(goto, raw_string, **(goto_kwargs if goto_kwargs else {}))

    def close_menu(self):
        """
        Shutdown menu; occurs when reaching the end node or using the quit command.
        """
        if not self._quitting:
            # avoid multiple calls from different sources
            self._quitting = True
            self.caller.cmdset.remove(EvMenuCmdSet)
            del self.caller.ndb._evmenu
            if self._persistent:
                self.caller.attributes.remove("_menutree_saved")
                self.caller.attributes.remove("_menutree_saved_startnode")
            if self.cmd_on_exit is not None:
                self.cmd_on_exit(self.caller, self)
            # special for template-generated menues
            del self.caller.db._evmenu_template_contents

    def print_debug_info(self, arg):
        """
        Messages the caller with the current menu state, for debug purposes.

        Args:
            arg (str): Arg to debug instruction, either nothing, 'full' or the name
                of a property to inspect.

        """
        all_props = inspect.getmembers(self)
        all_methods = [name for name, _ in inspect.getmembers(self, predicate=inspect.ismethod)]
        all_builtins = [name for name, _ in inspect.getmembers(self, predicate=inspect.isbuiltin)]
        props = {
            prop: value
            for prop, value in all_props
            if prop not in all_methods and prop not in all_builtins and not prop.endswith("__")
        }

        local = {
            key: var
            for key, var in locals().items()
            if key not in all_props and not key.endswith("__")
        }

        if arg:
            if arg in props:
                debugtxt = " |y* {}:|n\n{}".format(arg, props[arg])
            elif arg in local:
                debugtxt = " |y* {}:|n\n{}".format(arg, local[arg])
            elif arg == "full":
                debugtxt = (
                    "|yMENU DEBUG full ... |n\n"
                    + "\n".join(
                        "|y *|n {}: {}".format(key, val) for key, val in sorted(props.items())
                    )
                    + "\n |yLOCAL VARS:|n\n"
                    + "\n".join(
                        "|y *|n {}: {}".format(key, val) for key, val in sorted(local.items())
                    )
                    + "\n |y... END MENU DEBUG|n"
                )
            else:
                debugtxt = "|yUsage: menudebug full|<name of property>|n"
        else:
            debugtxt = (
                "|yMENU DEBUG properties ... |n\n"
                + "\n".join(
                    "|y *|n {}: {}".format(key, crop(to_str(val, force_string=True), width=50))
                    for key, val in sorted(props.items())
                )
                + "\n |yLOCAL VARS:|n\n"
                + "\n".join(
                    "|y *|n {}: {}".format(key, crop(to_str(val, force_string=True), width=50))
                    for key, val in sorted(local.items())
                )
                + "\n |y... END MENU DEBUG|n"
            )
        self.msg(debugtxt)

    def parse_input(self, raw_string):
        """
        Parses the incoming string from the menu user.

        Args:
            raw_string (str): The incoming, unmodified string
                from the user.
        Notes:
            This method is expected to parse input and use the result
            to relay execution to the relevant methods of the menu. It
            should also report errors directly to the user.

        """
        cmd = strip_ansi(raw_string.strip().lower())

        try:
            if self.options and cmd in self.options:
                # this will take precedence over the default commands
                # below
                goto, goto_kwargs, execfunc, exec_kwargs = self.options[cmd]
                self.run_exec_then_goto(execfunc, goto, raw_string, exec_kwargs, goto_kwargs)
            elif self.auto_look and cmd in ("look", "l"):
                self.display_nodetext()
            elif self.auto_help and cmd in ("help", "h"):
                self.display_helptext()
            elif self.auto_quit and cmd in ("quit", "q", "exit"):
                self.close_menu()
            elif self.debug_mode and cmd.startswith("menudebug"):
                self.print_debug_info(cmd[9:].strip())
            elif self.default:
                goto, goto_kwargs, execfunc, exec_kwargs = self.default
                self.run_exec_then_goto(execfunc, goto, raw_string, exec_kwargs, goto_kwargs)
            else:
                self.msg(_HELP_NO_OPTION_MATCH)
        except EvMenuGotoAbortMessage as err:
            # custom interrupt from inside a goto callable - print the message and
            # stay on the current node.
            self.msg(str(err))

    def display_nodetext(self):
        self.msg(self.nodetext)

    def display_helptext(self):
        self.msg(self.helptext)

    # formatters - override in a child class

    def nodetext_formatter(self, nodetext):
        """
        Format the node text itself.

        Args:
            nodetext (str): The full node text (the text describing the node).

        Returns:
            nodetext (str): The formatted node text.

        """
        return dedent(nodetext.strip("\n"), baseline_index=0).rstrip()

    def helptext_formatter(self, helptext):
        """
        Format the node's help text

        Args:
            helptext (str): The unformatted help text for the node.

        Returns:
            helptext (str): The formatted help text.

        """
        return dedent(helptext.strip("\n"), baseline_index=0).rstrip()

    def options_formatter(self, optionlist):
        """
        Formats the option block.

        Args:
            optionlist (list): List of (key, description) tuples for every
                option related to this node.
            caller (Object, Account or None, optional): The caller of the node.

        Returns:
            options (str): The formatted option display.

        """
        if not optionlist:
            return ""

        # column separation distance
        colsep = 4

        nlist = len(optionlist)

        # get the widest option line in the table.
        table_width_max = -1
        table = []
        for key, desc in optionlist:
            if key or desc:
                desc_string = ": %s" % desc if desc else ""
                table_width_max = max(
                    table_width_max,
                    max(m_len(p) for p in key.split("\n"))
                    + max(m_len(p) for p in desc_string.split("\n"))
                    + colsep,
                )
                raw_key = strip_ansi(key)
                if raw_key != key:
                    # already decorations in key definition
                    table.append(" |lc%s|lt%s|le%s" % (raw_key, key, desc_string))
                else:
                    # add a default white color to key
                    table.append(" |lc%s|lt|w%s|n|le%s" % (raw_key, raw_key, desc_string))
        ncols = _MAX_TEXT_WIDTH // table_width_max  # number of ncols

        if ncols < 0:
            # no visible option at all
            return ""

        ncols = ncols + 1 if ncols == 0 else ncols
        # get the amount of rows needed (start with 4 rows)
        nrows = 4
        while nrows * ncols < nlist:
            nrows += 1
        ncols = nlist // nrows  # number of full columns
        nlastcol = nlist % nrows  # number of elements in last column

        # get the final column count
        ncols = ncols + 1 if nlastcol > 0 else ncols
        if ncols > 1:
            # only extend if longer than one column
            table.extend([" " for i in range(nrows - nlastcol)])

        # build the actual table grid
        table = [table[icol * nrows : (icol * nrows) + nrows] for icol in range(0, ncols)]

        # adjust the width of each column
        for icol in range(len(table)):
            col_width = (
                max(max(m_len(p) for p in part.split("\n")) for part in table[icol]) + colsep
            )
            table[icol] = [pad(part, width=col_width + colsep, align="l") for part in table[icol]]

        # format the table into columns
        return str(EvTable(table=table, border="none"))

    def node_formatter(self, nodetext, optionstext):
        """
        Formats the entirety of the node.

        Args:
            nodetext (str): The node text as returned by `self.nodetext_formatter`.
            optionstext (str): The options display as returned by `self.options_formatter`.
            caller (Object, Account or None, optional): The caller of the node.

        Returns:
            node (str): The formatted node to display.

        """
        sep = self.node_border_char

        if self._session:
            screen_width = self._session.protocol_flags.get("SCREENWIDTH", {0: _MAX_TEXT_WIDTH})[0]
        else:
            screen_width = _MAX_TEXT_WIDTH

        nodetext_width_max = max(m_len(line) for line in nodetext.split("\n"))
        options_width_max = max(m_len(line) for line in optionstext.split("\n"))
        total_width = min(screen_width, max(options_width_max, nodetext_width_max))
        separator1 = sep * total_width + "\n\n" if nodetext_width_max else ""
        separator2 = "\n" + sep * total_width + "\n\n" if total_width else ""
        return separator1 + "|n" + nodetext + "|n" + separator2 + "|n" + optionstext


# -----------------------------------------------------------
#
# List node (decorator turning a node into a list with
#   look/edit/add functionality for the elements)
#
# -----------------------------------------------------------


def list_node(option_generator, select=None, pagesize=10):
    """
    Decorator for making an EvMenu node into a multi-page list node. Will add new options,
    prepending those options added in the node.

    Args:
        option_generator (callable or list): A list of strings indicating the options, or a callable
            that is called as option_generator(caller) to produce such a list.
        select (callable or str, optional): Node to redirect a selection to. Its `**kwargs` will
            contain the `available_choices` list and `selection` will hold one
            of the elements in that list.  If a callable, it will be called as
            `select(caller, menuchoice, **kwargs)` where menuchoice is the
            chosen option as a string and `available_choices` is the list of available
            options offered by the option_generator. The callable whould return
            the name of the target node to goto after this selection (or None to repeat the
            list-node).  Note that if this is not given, the decorated node
            must itself provide a way to continue from the node!
        pagesize (int): How many options to show per page.

    Example:
        ::

            def _selectfunc(caller, menuchoice, **kwargs):
                # menuchoice would be either 'foo' or 'bar' here
                # kwargs['available_choices'] would be the list ['foo', 'bar']
                return "the_next_node_to_go_to"

            @list_node(['foo', 'bar'], _selectfunc)
            def node_index(caller):
                text = "describing the list"
                return text, []

    Notes:
        All normal `goto` or `exec` callables returned from the decorated nodes will, if they accept
        `**kwargs`, get a new kwarg `available_choices` injected. This is the ordered list of named
        options (descs) visible on the current node page.

    """

    def decorator(func):
        def _select_parser(caller, raw_string, **kwargs):
            """
            Parse the select action
            """
            available_choices = kwargs.get("available_choices", [])

            try:
                index = int(raw_string.strip()) - 1
                selection = available_choices[index]
            except Exception:
                caller.msg("|rInvalid choice.|n")
            else:
                if callable(select):
                    try:
                        if bool(getargspec(select).keywords):
                            return select(caller, selection, available_choices=available_choices)
                        else:
                            return select(caller, selection)
                    except Exception:
                        logger.log_trace()
                elif select:
                    # we assume a string was given, we inject the result into the kwargs
                    # to pass on to the next node
                    kwargs["selection"] = selection
                    return str(select)
            # this means the previous node will be re-run with these same kwargs
            return None

        def _list_node(caller, raw_string, **kwargs):

            option_list = (
                option_generator(caller) if callable(option_generator) else option_generator
            )

            npages = 0
            page_index = 0
            page = []
            options = []

            if option_list:
                nall_options = len(option_list)
                pages = [
                    option_list[ind : ind + pagesize] for ind in range(0, nall_options, pagesize)
                ]
                npages = len(pages)

                page_index = max(0, min(npages - 1, kwargs.get("optionpage_index", 0)))
                page = pages[page_index]

            text = ""
            extra_text = None

            # dynamic, multi-page option list. Each selection leads to the `select`
            # callback being called with a result from the available choices
            options.extend(
                [
                    {"desc": opt, "goto": (_select_parser, {"available_choices": page})}
                    for opt in page
                ]
            )

            if npages > 1:
                # if the goto callable returns None, the same node is rerun, and
                # kwargs not used by the callable are passed on to the node. This
                # allows us to call ourselves over and over, using different kwargs.
                options.append(
                    {
                        "key": ("|Wcurrent|n", "c"),
                        "desc": "|W({}/{})|n".format(page_index + 1, npages),
                        "goto": (lambda caller: None, {"optionpage_index": page_index}),
                    }
                )
                if page_index > 0:
                    options.append(
                        {
                            "key": ("|wp|Wrevious page|n", "p"),
                            "goto": (lambda caller: None, {"optionpage_index": page_index - 1}),
                        }
                    )
                if page_index < npages - 1:
                    options.append(
                        {
                            "key": ("|wn|Wext page|n", "n"),
                            "goto": (lambda caller: None, {"optionpage_index": page_index + 1}),
                        }
                    )

            # add data from the decorated node

            decorated_options = []
            supports_kwargs = bool(getargspec(func).keywords)
            try:
                if supports_kwargs:
                    text, decorated_options = func(caller, raw_string, **kwargs)
                else:
                    text, decorated_options = func(caller, raw_string)
            except TypeError:
                try:
                    if supports_kwargs:
                        text, decorated_options = func(caller, **kwargs)
                    else:
                        text, decorated_options = func(caller)
                except Exception:
                    raise
            except Exception:
                logger.log_trace()
            else:
                if isinstance(decorated_options, dict):
                    decorated_options = [decorated_options]
                else:
                    decorated_options = make_iter(decorated_options)

            extra_options = []
            if isinstance(decorated_options, dict):
                decorated_options = [decorated_options]
            for eopt in decorated_options:
                cback = ("goto" in eopt and "goto") or ("exec" in eopt and "exec") or None
                if cback:
                    signature = eopt[cback]
                    if callable(signature):
                        # callable with no kwargs defined
                        eopt[cback] = (signature, {"available_choices": page})
                    elif is_iter(signature):
                        if len(signature) > 1 and isinstance(signature[1], dict):
                            signature[1]["available_choices"] = page
                            eopt[cback] = signature
                        elif signature:
                            # a callable alone in a tuple (i.e. no previous kwargs)
                            eopt[cback] = (signature[0], {"available_choices": page})
                        else:
                            # malformed input.
                            logger.log_err(
                                "EvMenu @list_node decorator found "
                                "malformed option to decorate: {}".format(eopt)
                            )
                extra_options.append(eopt)

            options.extend(extra_options)
            text = text + "\n\n" + extra_text if extra_text else text

            return text, options

        return _list_node

    return decorator


# -------------------------------------------------------------------------------------------------
#
# Simple input shortcuts
#
# -------------------------------------------------------------------------------------------------


class CmdGetInput(Command):
    """
    Enter your data and press return.
    """

    key = _CMD_NOMATCH
    aliases = _CMD_NOINPUT

    def func(self):
        """This is called when user enters anything."""
        caller = self.caller
        try:
            getinput = caller.ndb._getinput
            if not getinput and hasattr(caller, "account"):
                getinput = caller.account.ndb._getinput
                caller = caller.account
            callback = getinput._callback

            caller.ndb._getinput._session = self.session
            prompt = caller.ndb._getinput._prompt
            args = caller.ndb._getinput._args
            kwargs = caller.ndb._getinput._kwargs
            result = self.raw_string.rstrip()  # we strip the ending line break caused by sending

            ok = not callback(caller, prompt, result, *args, **kwargs)
            if ok:
                # only clear the state if the callback does not return
                # anything
                del caller.ndb._getinput
                caller.cmdset.remove(InputCmdSet)
        except Exception:
            # make sure to clean up cmdset if something goes wrong
            caller.msg("|rError in get_input. Choice not confirmed (report to admin)|n")
            logger.log_trace("Error in get_input")
            caller.cmdset.remove(InputCmdSet)


class InputCmdSet(CmdSet):
    """
    This stores the input command
    """

    key = "input_cmdset"
    priority = 1
    mergetype = "Replace"
    no_objs = True
    no_exits = True
    no_channels = False

    def at_cmdset_creation(self):
        """called once at creation"""
        self.add(CmdGetInput())


class _Prompt(object):
    """Dummy holder"""

    pass


def get_input(caller, prompt, callback, session=None, *args, **kwargs):
    """
    This is a helper function for easily request input from
    the caller.

    Args:
        caller (Account or Object): The entity being asked
            the question. This should usually be an object
            controlled by a user.
        prompt (str): This text will be shown to the user,
            in order to let them know their input is needed.
        callback (callable): A function that will be called
            when the user enters a reply. It must take three
            arguments: the `caller`, the `prompt` text and the
            `result` of the input given by the user. If the
            callback doesn't return anything or return False,
            the input prompt will be cleaned up and exited. If
            returning True, the prompt will remain and continue to
            accept input.
        session (Session, optional): This allows to specify the
            session to send the prompt to. It's usually only
            needed if `caller` is an Account in multisession modes
            greater than 2. The session is then updated by the
            command and is available (for example in callbacks)
            through `caller.ndb.getinput._session`.
        args, kwargs (optional): Extra arguments will be
            passed to the fall back function as a list 'args'
            and all keyword arguments as a dictionary 'kwargs'.
            To utilise `*args` and `**kwargs`, a value for the
            session argument must be provided (None by default)
            and the callback function must take `*args` and
            `**kwargs` as arguments.

    Raises:
        RuntimeError: If the given callback is not callable.

    Notes:
        The result value sent to the callback is raw and not
        processed in any way. This means that you will get
        the ending line return character from most types of
        client inputs. So make sure to strip that before
        doing a comparison.

        When the prompt is running, a temporary object
        `caller.ndb._getinput` is stored; this will be removed
        when the prompt finishes.
        If you need the specific Session of the caller (which
        may not be easy to get if caller is an account in higher
        multisession modes), then it is available in the
        callback through `caller.ndb._getinput._session`.

        Chaining get_input functions will result in the caller
        stacking ever more instances of InputCmdSets. Whilst
        they will all be cleared on concluding the get_input
        chain, EvMenu should be considered for anything beyond
        a single question.

    """
    if not callable(callback):
        raise RuntimeError("get_input: input callback is not callable.")
    caller.ndb._getinput = _Prompt()
    caller.ndb._getinput._callback = callback
    caller.ndb._getinput._prompt = prompt
    caller.ndb._getinput._session = session
    caller.ndb._getinput._args = args
    caller.ndb._getinput._kwargs = kwargs
    caller.cmdset.add(InputCmdSet)
    caller.msg(prompt, session=session)


# -------------------------------------------------------------
#
# Menu generation from menu template string
#
# -------------------------------------------------------------

_RE_NODE = re.compile(r"##\s*?NODE\s+?(?P<nodename>\S[\S\s]*?)$", re.I + re.M)
_RE_OPTIONS_SEP = re.compile(r"##\s*?OPTIONS\s*?$", re.I + re.M)
_RE_CALLABLE = re.compile(r"\S+?\(\)", re.I + re.M)
_RE_CALLABLE = re.compile(r"(?P<funcname>\S+?)(?:\((?P<kwargs>[\S\s]+?)\)|\(\))", re.I + re.M)

_HELP_NO_OPTION_MATCH = _("Choose an option or try 'help'.")

_OPTION_INPUT_MARKER = ">"
_OPTION_ALIAS_MARKER = ";"
_OPTION_SEP_MARKER = ":"
_OPTION_CALL_MARKER = "->"
_OPTION_COMMENT_START = "#"


# Input/option/goto handler functions that allows for dynamically generated
# nodes read from the menu template.


def _process_callable(caller, goto, goto_callables, raw_string, current_nodename, kwargs):
    """
    Central helper for parsing a goto-callable (`funcname(**kwargs)`) out of
    the right-hand-side of the template options and map this to an actual
    callable registered with the template generator. This involves parsing the
    func-name and running literal-eval on its kwargs.

    """
    match = _RE_CALLABLE.match(goto)
    if match:
        gotofunc = match.group("funcname")
        gotokwargs = match.group("kwargs") or ""
        if gotofunc in goto_callables:
            for kwarg in gotokwargs.split(","):
                if kwarg and "=" in kwarg:
                    key, value = [part.strip() for part in kwarg.split("=", 1)]
                    if key in (
                        "evmenu_goto",
                        "evmenu_gotomap",
                        "_current_nodename",
                        "evmenu_current_nodename",
                        "evmenu_goto_callables",
                    ):
                        raise RuntimeError(
                            f"EvMenu template error: goto-callable '{goto}' uses a "
                            f"kwarg ({kwarg}) that is reserved for the EvMenu templating "
                            "system. Rename the kwarg."
                        )
                    try:
                        key = literal_eval(key)
                    except ValueError:
                        pass
                    try:
                        value = literal_eval(value)
                    except ValueError:
                        pass
                    kwargs[key] = value

                goto = goto_callables[gotofunc](caller, raw_string, **kwargs)
    if goto is None:
        return goto, {"generated_nodename": current_nodename}
    return goto, {"generated_nodename": goto}


def _generated_goto_func(caller, raw_string, **kwargs):
    """
    This rerouter handles normal direct goto func call matches.

    key : ... -> goto_callable(**kwargs)

    """
    goto = kwargs["evmenu_goto"]
    goto_callables = kwargs["evmenu_goto_callables"]
    current_nodename = kwargs["evmenu_current_nodename"]
    return _process_callable(caller, goto, goto_callables, raw_string, current_nodename, kwargs)


def _generated_input_goto_func(caller, raw_string, **kwargs):
    """
    This goto-func acts as a rerouter for >-type line parsing (by acting as the
    _default option). The patterns discovered in the menu maps to different
    *actual* goto-funcs. We map to those here.

    >pattern: ... -> goto_callable

    """
    gotomap = kwargs["evmenu_gotomap"]
    goto_callables = kwargs["evmenu_goto_callables"]
    current_nodename = kwargs["evmenu_current_nodename"]
    raw_string = raw_string.strip("\n")  # strip is necessary to catch empty return

    # start with glob patterns
    for pattern, goto in gotomap.items():
        if fnmatch(raw_string.lower(), pattern):
            return _process_callable(
                caller, goto, goto_callables, raw_string, current_nodename, kwargs
            )
    # no glob pattern match; try regex
    for pattern, goto in gotomap.items():
        if pattern and re.match(pattern, raw_string.lower(), flags=re.I + re.M):
            return _process_callable(
                caller, goto, goto_callables, raw_string, current_nodename, kwargs
            )
    # no match, show error
    raise EvMenuGotoAbortMessage(_HELP_NO_OPTION_MATCH)


def _generated_node(caller, raw_string, **kwargs):
    """
    Every node in the templated menu will be this node, but with dynamically
    changing text/options. It must be a global function like this because
    otherwise we could not make the templated-menu persistent.

    """
    text, options = caller.db._evmenu_template_contents[kwargs["_current_nodename"]]
    return text, options


def parse_menu_template(caller, menu_template, goto_callables=None):
    """
    Parse menu-template string. The main function of the EvMenu templating system.

    Args:
        caller (Object or Account): Entity using the menu.
        menu_template (str): Menu described using the templating format.
        goto_callables (dict, optional): Mapping between call-names and callables
            on the form `callable(caller, raw_string, **kwargs)`. These are what is
            available to use in the `menu_template` string.

    Returns:
        dict: A `{"node": nodefunc}` menutree suitable to pass into EvMenu.

    """

    def _validate_kwarg(goto, kwarg):
        """
        Validate goto-callable kwarg is on correct form.
        """
        if not "=" in kwarg:
            raise RuntimeError(
                f"EvMenu template error: goto-callable '{goto}' has a "
                f"non-kwarg argument ({kwarg}). All callables in the "
                "template must have only keyword-arguments, or no "
                "args at all."
            )
        key, _ = [part.strip() for part in kwarg.split("=", 1)]
        if key in (
            "evmenu_goto",
            "evmenu_gotomap",
            "_current_nodename",
            "evmenu_current_nodename",
            "evmenu_goto_callables",
        ):
            raise RuntimeError(
                f"EvMenu template error: goto-callable '{goto}' uses a "
                f"kwarg ({kwarg}) that is reserved for the EvMenu templating "
                "system. Rename the kwarg."
            )

    def _parse_options(nodename, optiontxt, goto_callables):
        """
        Parse option section into option dict.
        """
        options = []
        optiontxt = optiontxt[0].strip() if optiontxt else ""
        optionlist = [optline.strip() for optline in optiontxt.split("\n")]
        inputparsemap = {}

        for inum, optline in enumerate(optionlist):
            if optline.startswith(_OPTION_COMMENT_START) or _OPTION_SEP_MARKER not in optline:
                # skip comments or invalid syntax
                continue
            key = ""
            desc = ""
            pattern = None

            key, goto = [part.strip() for part in optline.split(_OPTION_SEP_MARKER, 1)]

            # desc -> goto
            if _OPTION_CALL_MARKER in goto:
                desc, goto = [part.strip() for part in goto.split(_OPTION_CALL_MARKER, 1)]

            # validate callable
            match = _RE_CALLABLE.match(goto)
            if match:
                kwargs = match.group("kwargs")
                if kwargs:
                    for kwarg in kwargs.split(","):
                        _validate_kwarg(goto, kwarg)

            # parse key [;aliases|pattern]
            key = [part.strip() for part in key.split(_OPTION_ALIAS_MARKER)]
            if not key:
                # fall back to this being the Nth option
                key = [f"{inum + 1}"]
            main_key = key[0]

            if main_key.startswith(_OPTION_INPUT_MARKER):
                # if we have a pattern, build the arguments for _default later
                pattern = main_key[len(_OPTION_INPUT_MARKER) :].strip()
                inputparsemap[pattern] = goto
            else:
                # a regular goto string/callable target
                option = {
                    "key": key,
                    "goto": (
                        _generated_goto_func,
                        {
                            "evmenu_goto": goto,
                            "evmenu_current_nodename": nodename,
                            "evmenu_goto_callables": goto_callables,
                        },
                    ),
                }
                if desc:
                    option["desc"] = desc
                options.append(option)

        if inputparsemap:
            # if this exists we must create a _default entry too
            options.append(
                {
                    "key": "_default",
                    "goto": (
                        _generated_input_goto_func,
                        {
                            "evmenu_gotomap": inputparsemap,
                            "evmenu_current_nodename": nodename,
                            "evmenu_goto_callables": goto_callables,
                        },
                    ),
                }
            )

        return options

    def _parse(caller, menu_template, goto_callables):
        """
        Parse the menu string format into a node tree.
        """
        nodetree = {}
        splits = _RE_NODE.split(menu_template)
        splits = splits[1:] if splits else []

        # from evennia import set_trace;set_trace(term_size=(140,120))
        content_map = {}
        for node_ind in range(0, len(splits), 2):
            nodename, nodetxt = splits[node_ind], splits[node_ind + 1]
            text, *optiontxt = _RE_OPTIONS_SEP.split(nodetxt, maxsplit=2)
            options = _parse_options(nodename, optiontxt, goto_callables)
            content_map[nodename] = (text, options)
            nodetree[nodename] = _generated_node
        caller.db._evmenu_template_contents = content_map

        return nodetree

    return _parse(caller, menu_template, goto_callables)


def template2menu(
    caller, menu_template, goto_callables=None, startnode="start", persistent=False, **kwargs,
):
    """
    Helper function to generate and start an EvMenu based on a menu template
    string. This will internall call `parse_menu_template` and run a default
    EvMenu with its results.

    Args:
        caller (Object or Account): The entity using the menu.
        menu_template (str): The menu-template string describing the content
            and structure of the menu. It can also be the python-path to, or a module
            containing a `MENU_TEMPLATE` global variable with the template.
        goto_callables (dict, optional): Mapping of callable-names to
            module-global objects to reference by name in the menu-template.
            Must be on the form `callable(caller, raw_string, **kwargs)`.
        startnode (str, optional): The name of the startnode, if not 'start'.
        persistent (bool, optional): If the generated menu should be persistent.
        **kwargs: All kwargs will be passed into EvMenu.

    Returns:
        EvMenu: The generated EvMenu.

    """
    goto_callables = goto_callables or {}
    menu_tree = parse_menu_template(caller, menu_template, goto_callables)
    return EvMenu(caller, menu_tree, persistent=persistent, **kwargs,)
