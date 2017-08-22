import dateutil.parser

class Event(object):

    ASSIGNED = 'assigned'
    LABELLED = 'labeled'
    ADDED_TO_PROJECT = 'added_to_project'
    GENERIC = 'UNLOVED'

    def __init__(self, event):
        self.timestamp = dateutil.parser.parse(event['created_at'])
        self.type = event['event']
        self.event = event

    @classmethod
    def from_json(cls, event):
        event_name = event['event']
        if event_name == 'labeled':
            return LabelEvent(event)
        elif event_name == 'assigned':
            return AssignedEvent(event)
        else:
            return Event(event)

    def __str__(self):
        return '%s %s' % (self.timestamp, self.type)

class AssignedEvent(Event):

    def __init__(self, event):
        super(AssignedEvent, self).__init__(event)
        self.assignee = event['assignee']['login']

    def __str__(self):
        return '%s %s (%s)' % (self.timestamp, self.type, self.assignee)

class LabelEvent(Event):

    def __init__(self, event):
        super(LabelEvent, self).__init__(event)
        self.label = event['label']['name']

    def __str__(self):
        return '%s %s (%s)' % (self.timestamp, self.type, self.label)
