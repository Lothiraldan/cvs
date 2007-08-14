import getopt

def fancyopts(args, options, state):
    long = []
    short = ''
    map = {}
    dt = {}

    for s, l, d, c in options:
        pl = l.replace('-', '_')
        map['-'+s] = map['--'+l] = pl
        if isinstance(d, list):
            state[pl] = d[:]
        else:
            state[pl] = d
        dt[pl] = type(d)
        if (d is not None and d is not True and d is not False and
            not callable(d)):
            if s: s += ':'
            if l: l += '='
        if s: short = short + s
        if l: long.append(l)

    opts, args = getopt.getopt(args, short, long)

    for opt, arg in opts:
        if dt[map[opt]] is type(fancyopts): state[map[opt]](state, map[opt], arg)
        elif dt[map[opt]] is type(1): state[map[opt]] = int(arg)
        elif dt[map[opt]] is type(''): state[map[opt]] = arg
        elif dt[map[opt]] is type([]): state[map[opt]].append(arg)
        elif dt[map[opt]] is type(None): state[map[opt]] = True
        elif dt[map[opt]] is type(False): state[map[opt]] = True

    return args

