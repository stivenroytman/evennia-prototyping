"""
Containers

Containers are storage classes usually initialized from a setting. They
represent Singletons and acts as a convenient place to find resources (
available as properties on the singleton)

evennia.GLOBAL_SCRIPTS
evennia.OPTION_CLASSES

"""


from django.conf import settings
from evennia.utils.utils import class_from_module, callables_from_module
from evennia.utils import logger


SCRIPTDB = None


class Container(object):
    """
    Base container class. A container is simply a storage object whose
    properties can be acquired as a property on it. This is generally
    considered a read-only affair.

    The container is initialized by a list of modules containing callables.

    """

    storage_modules = []

    def __init__(self):
        """
        Read data from module.

        """
        self.loaded_data = None

    def load_data(self):
        """
        Delayed import to avoid eventual circular imports from inside
        the storage modules.

        """
        if self.loaded_data is None:
            self.loaded_data = {}
            for module in self.storage_modules:
                self.loaded_data.update(callables_from_module(module))

    def __getattr__(self, key):
        return self.get(key)

    def get(self, key, default=None):
        """
        Retrive data by key (in case of not knowing it beforehand).

        Args:
            key (str): The name of the script.
            default (any, optional): Value to return if key is not found.

        Returns:
            any (any): The data loaded on this container.

        """
        self.load_data()
        return self.loaded_data.get(key, default)

    def all(self):
        """
        Get all stored data

        Returns:
            scripts (list): All global script objects stored on the container.

        """
        self.load_data()
        return list(self.loaded_data.values())


class OptionContainer(Container):
    """
    Loads and stores the final list of OPTION CLASSES.

    Can access these as properties or dictionary-contents.
    """

    storage_modules = settings.OPTION_CLASS_MODULES


class GlobalScriptContainer(Container):
    """
    Simple Handler object loaded by the Evennia API to contain and manage a
    game's Global Scripts. This will list global Scripts created on their own
    but will also auto-(re)create scripts defined in `settings.GLOBAL_SCRIPTS`.

    Example:
        import evennia
        evennia.GLOBAL_SCRIPTS.scriptname

    Note:
        This does not use much of the BaseContainer since it's not loading
        callables from settings but a custom dict of tuples.

    """

    def __init__(self):
        """
        Note: We must delay loading of typeclasses since this module may get
        initialized before Scripts are actually initialized.

        """
        self.typeclass_storage = None
        self.loaded_data = {
            key: {} if data is None else data for key, data in settings.GLOBAL_SCRIPTS.items()
        }

    def _get_scripts(self, key=None, default=None):
        global SCRIPTDB
        if not SCRIPTDB:
            from evennia.scripts.models import ScriptDB as SCRIPTDB
        if key:
            try:
                return SCRIPTDB.objects.get(db_key__exact=key, db_obj__isnull=True)
            except SCRIPTDB.DoesNotExist:
                return default
        else:
            return SCRIPTDB.objects.filter(db_obj__isnull=True)

    def _load_script(self, key):
        self.load_data()

        typeclass = self.typeclass_storage[key]
        found = typeclass.objects.filter(db_key=key).first()
        interval = self.loaded_data[key].get("interval", None)
        start_delay = self.loaded_data[key].get("start_delay", None)
        repeats = self.loaded_data[key].get("repeats", 0)
        desc = self.loaded_data[key].get("desc", "")

        if not found:
            logger.log_info(f"GLOBAL_SCRIPTS: (Re)creating {key} ({typeclass}).")
            new_script, errors = typeclass.create(
                key=key,
                persistent=True,
                interval=interval,
                start_delay=start_delay,
                repeats=repeats,
                desc=desc,
            )
            if errors:
                logger.log_err("\n".join(errors))
                return None

            new_script.start()
            return new_script

        if (
            (found.interval != interval)
            or (found.start_delay != start_delay)
            or (found.repeats != repeats)
        ):
            found.restart(interval=interval, start_delay=start_delay, repeats=repeats)
        if found.desc != desc:
            found.desc = desc
        return found

    def start(self):
        """
        Called last in evennia.__init__ to initialize the container late
        (after script typeclasses have finished loading).

        We include all global scripts in the handler and
        make sure to auto-load time-based scripts.

        """
        # populate self.typeclass_storage
        self.load_data()

        # start registered scripts
        for key in self.loaded_data:
            self._load_script(key)

    def load_data(self):
        """
        This delayed import avoids trying to load Scripts before they are
        initialized.

        """
        if self.typeclass_storage is None:
            self.typeclass_storage = {}
            for key, data in self.loaded_data.items():
                try:
                    typeclass = data.get("typeclass", settings.BASE_SCRIPT_TYPECLASS)
                    self.typeclass_storage[key] = class_from_module(typeclass)
                except ImportError as err:
                    logger.log_err(
                        f"GlobalScriptContainer could not start global script {key}: {err}"
                    )

    def get(self, key, default=None):
        """
        Retrive data by key (in case of not knowing it beforehand). Any
        scripts that are in settings.GLOBAL_SCRIPTS that are not found
        will be recreated on-demand.

        Args:
            key (str): The name of the script.
            default (any, optional): Value to return if key is not found
                at all on this container (i.e it cannot be loaded at all).

        Returns:
            any (any): The data loaded on this container.
        """
        res = self._get_scripts(key)
        if not res:
            if key in self.loaded_data:
                # recreate if we have the info
                return self._load_script(key) or default
            return default
        return res

    def all(self):
        """
        Get all global scripts. Note that this will not auto-start
        scripts defined in settings.

        Returns:
            scripts (list): All global script objects stored on the container.

        """
        self.typeclass_storage = None
        self.load_data()
        for key in self.loaded_data:
            self._load_script(key)
        return self._get_scripts(None)


# Create all singletons

GLOBAL_SCRIPTS = GlobalScriptContainer()
OPTION_CLASSES = OptionContainer()
