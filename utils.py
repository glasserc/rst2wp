import re

def replace_newlines(txt):
    '''Eliminate newlines from txt.

    Wordpress's post API tries to format text, turns newlines into
    <br/>s, etc. Since we're giving it already-formatted HTML,
    there's no need for that behavior. Instead we turn newlines
    into spaces, which is safe because HTML mandates that multiple
    whitespaces are identical to one whitespace.

    The only time this doesn't work is when handling <pre>
    elements. Thus, we handle those specially.'''
    start = 0                          # start eliminating from here
    pre = re.compile("<pre( [^>]*)?>") # actual parsing? fuck that noise!
    end_pre = re.compile("</pre>")     # whew, no </pre class="...">

    # Loop invariant: start is the index at which text has already
    # been processed. This means it either ends a </pre> or 0.
    #
    # <pre>hi there</pre>abcde fgh ijklm<pre>foo bar baz</pre>nopqrstu
    # start -------------|
    # m.start() ------------------------|
    while True:
        m = pre.search(txt, start)
        if not m: break

        txt = (txt[:start] +     # already replaced
               txt[start:m.start()].replace('\n', ' ') +  # replace till next <pre>
               txt[m.start():])    # <pre> and afterwards

        # Indexes could change between start and m.start(), since
        # that's where we replace text. (They don't, but whatever.)
        # So to advance start, we search starting from start (instead
        # of m.start()).
        m = end_pre.search(txt, start)

        if not m: break    # couldn't keep the invariant
        start = m.end()

    # No <pre> blocks between start and end of string, but still
    # have to replace newlines there
    txt = txt[:start] + txt[start:].replace('\n', ' ')
    return txt

def list_wrap(obj):
    if isinstance(obj, list): return obj
    return [obj]

# Stolen from Dive Into Python: http://diveintopython3.org/your-first-python-program.html

SUFFIXES = {1000: ['KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'],
            1024: ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']}

def approximate_size(size, a_kilobyte_is_1024_bytes=True):
    '''Convert a file size to human-readable form.

    Keyword arguments:
    size -- file size in bytes
    a_kilobyte_is_1024_bytes -- if True (default), use multiples of 1024
                                if False, use multiples of 1000

    Returns: string

    '''
    if size < 0:
        raise ValueError('number must be non-negative')

    multiple = 1024 if a_kilobyte_is_1024_bytes else 1000
    for suffix in SUFFIXES[multiple]:
        size /= multiple
        if size < multiple:
            return '{0:.1f} {1}'.format(size, suffix)

    raise ValueError('number too large')
