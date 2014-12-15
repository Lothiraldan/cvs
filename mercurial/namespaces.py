from i18n import _
from mercurial import util

def tolist(val):
    """
    a convenience method to return an empty list instead of None
    """
    if val is None:
        return []
    else:
        return [val]

class namespaces(object):
    """
    provides an interface to register a generic many-to-many mapping between
    some (namespaced) names and nodes. The goal here is to control the
    pollution of jamming things into tags or bookmarks (in extension-land) and
    to simplify internal bits of mercurial: log output, tab completion, etc.

    More precisely, we define a list of names (the namespace), a mapping of
    names to nodes, and a mapping from nodes to names. Each mapping
    returns a list of nodes.

    Furthermore, each name mapping will be passed a name to lookup which might
    not be in its domain. In this case, each method should return an empty list
    and not raise an error.

    We'll have a dictionary '_names' where each key is a namespace and
    its value is a dictionary of functions:
      'templatename': name to use for templating (usually the singular form
                      of the plural namespace name)
      'namemap': function that takes a name and returns a list of nodes
      'nodemap': function that takes a node and returns a list of names
    """

    _names_version = 0

    def __init__(self):
        self._names = util.sortdict()

        addns = self.addnamespace

        # we need current mercurial named objects (bookmarks, tags, and
        # branches) to be initialized somewhere, so that place is here
        addns("bookmarks", "bookmark",
              lambda repo, name: tolist(repo._bookmarks.get(name)),
              lambda repo, name: repo.nodebookmarks(name))

        addns("tags", "tag",
              lambda repo, name: tolist(repo._tagscache.tags.get(name)),
              lambda repo, name: repo.nodetags(name))

        addns("branches", "branch",
              lambda repo, name: tolist(repo.branchtip(name)),
              lambda repo, node: [repo[node].branch()])

    def addnamespace(self, namespace, templatename, namemap, nodemap,
                     order=None):
        """
        register a namespace

        namespace: the name to be registered (in plural form)
        templatename: the name to use for templating
        namemap: function that inputs a node, output name(s)
        nodemap: function that inputs a name, output node(s)
        order: optional argument to specify the order of namespaces
               (e.g. 'branches' should be listed before 'bookmarks')
        """
        val = {'templatename': templatename,
               'namemap': namemap,
               'nodemap': nodemap}
        if order is not None:
            self._names.insert(order, namespace, val)
        else:
            self._names[namespace] = val

    def singlenode(self, repo, name):
        """
        Return the 'best' node for the given name. Best means the first node
        in the first nonempty list returned by a name-to-nodes mapping function
        in the defined precedence order.

        Raises a KeyError if there is no such node.
        """
        for ns, v in self._names.iteritems():
            n = v['namemap'](repo, name)
            if n:
                # return max revision number
                if len(n) > 1:
                    cl = repo.changelog
                    maxrev = max(cl.rev(node) for node in n)
                    return cl.node(maxrev)
                return n[0]
        raise KeyError(_('no such name: %s') % name)

    def templatename(self, namespace):
        """method that returns the template name of a namespace"""
        return self._names[namespace]['templatename']
