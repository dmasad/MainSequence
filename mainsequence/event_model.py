from collections import defaultdict
import random
import json
import math

class EventModel:
    '''
    A model of random events influencing and influenced by a world state.
    '''

    # =================
    # Static condition checkers

    conditions_checkers = {
        "ANY": lambda state, tag, label: tag in state and len(state[tag]) > 0,
        "NONE": lambda state, tag, label: (tag not in state 
                                           or len(state[tag])==0),
        "EXCLUDE": lambda state, tag, label: (tag in state and 
                            len(state[tag]) > 0 and label not in state[tag]),
        "IN": lambda state, tag, label: tag in state and label in state[tag]
    }


    def __init__(self, event_grammar, repeating_events=True):
        '''
        Create a new event model generator.

        Args:
            event_grammar: Either a dictionary with a valid grammar, or a path
                           to a .json file to load with a valid grammar.
            repeating_events: If True, the model may choose events more than
                              once, if they are still valid; if False, each
                              event may occur no more than once.
        '''

        if type(event_grammar) is dict:
            self.grammar = event_grammar
        elif event_grammar[-4:] == "json":
            with open(event_grammar) as f:
                self.grammar = json.load(f)
        
        self.events = self.grammar["events"]
        if not self.validate_events():
            raise Exception("Invalid grammar")

        self.repeating_events = repeating_events
        self.starting_state = dict()
        if "starting_state" in self.grammar:
            self.starting_state = dict(self.grammar["starting_state"])
        self.stability = 1
        if "stability" in self.grammar:
            self.stability = self.grammar["stability"]
        self.reset()

    def reset(self):
        '''
        Reset the model to its starting state, and remove the history.
        '''

        self.state = defaultdict(list)
        self.state_history = []
        self.log = []
        for tag, values in self.starting_state.items():
            self.state[tag] = values
        self.store_state()
        self.log.append("<START>")
        self.running = True

    @classmethod
    def check_preconditions(cls, state, preconditions):
        '''
        Check whether a set of preconditions are consistent with a state.

        args:
            state: A valid world state, consisting of a dictionary with tags as
                   keys and lists of labels as values. 
            preconditions: A valid dictionary of preconditions, with tags as
                           keys and valid precondition strings as values.
        Returns:
            True if the preconditions are consistent with the state; or False
        '''
        if len(preconditions) == 0:
            return True
        valid = []

        for tag, condition in preconditions.items():
            conditions = cls._parse_conditions(condition)
            for label, check in conditions:
                checker = cls.conditions_checkers[check]
                validity = checker(state, tag, label)
                valid.append(validity)
        return all(valid)

    @staticmethod
    def _parse_conditions(condition_str):
        '''
        Parse a condition label string.

        Syntax:
            conditions are separated by a semi-colon; all conditions must apply
            to labels of the same tag.
            "*": Any label must be associated with the tag
            "!": No labels may be associated with the tag
            "Label": The label must be associated with the tag.
            "!Label": There must be labels associated with the tag, and Label
                may not be one of them.
        '''

        conditions = [word.strip() for word in condition_str.split(";")]
        parsed_conditions = []
        for condition in conditions:
            if len(condition) == 1:
                label = None
                if condition == "*":
                    check = "ANY"
                elif condition == "!":
                    check = "NONE"
                else:
                    raise Exception("Invalid condition: {}".format(condition))
            else:
                if condition[0] == "!":
                    check = "EXCLUDE"
                    label = condition[1:]
                else:
                    check = "IN"
                    label = condition
            parsed_conditions.append((label, check))
        return parsed_conditions


    def filter_events(self, state=None):
        '''
        Find all events with preconditions consistent with the (or a) state.

        Args:
            state: (Optional) a world state dict; if None, uses the model state

        Returns:
            A dictionary mapping valid event names to event dicts
        '''

        if not state:
            state = self.state
            options = {}
        for event in self.events:
            if not self.repeating_events:
                if event["name"] in self.log:
                    continue
            if self.check_preconditions(state, event["preconditions"]):
                options[event["name"]] = event
        return options

    def get_weight(self, event, state=None):
        '''
        Get the probability weight of an event based on the (a) state.

        Adds together the event's weight, if given (default is 0) and any
        relevant influence modifiers it has.

        Args:
            event: An event dict
            state: (optional) the state to get the weight for; 
                   if None, uses the current model state.
        '''
        weight = 0
        if "weight" in event:
            weight = event["weight"]

        if "influences" not in event:
            return weight

        if not state:
            state = self.state

        for tag, values in event["influences"].items():
            for condition, w in values.items():
                conditions = self._parse_conditions(condition)
                valid = [self.conditions_checkers[check](state, tag, label) 
                         for label, check in conditions]
                if all(valid):
                    weight += w
        return weight


    def execute_event(self, event):
        '''
        Execute a single event and update the world state accordingly.

        Parse the effects of the event and use them to update the model
        world state.

        Args:
            event: An event dictionary
        '''
        for tag, label in event["effects"].items():
            if tag == "<END>":
                self.running = False
                return
            changes = [word.strip() for word in label.split(";")]
            for change in changes:
                if len(change) == 0:
                    if not label.strip():
                        self.state[tag] = []
                elif change[0] == "+":
                    self.state[tag].append(change[1:])
                elif change[0] == "-":
                    if change[1:] in self.state[tag]:
                        self.state[tag].remove(change[1:])
                else:
                    self.state[tag] = [change]

    def advance(self, verbose=True):
        '''
        Choose, execute and log the next event.

        Filters all possible events to find ones that are consistent with
        the current world state. Finds weights for each of them, and chooses
        one based on the weight. Then executes the event, updates the world
        state, and adds the event to the log.

        Args:
            verbose: If False, advances silently. If True, print the executed
                     event; if "Full", also print the possible events, and
                     their associated weights.
        '''

        options = self.filter_events()
        choices = {name: self.get_weight(event)
                   for name, event in options.items()}
        if verbose == "Full":
            print("\t", choices)
        if len(options) == 0:
            self.running = False
            self.log.append("<END>")
            return

        next_event = options[self.weighted_random(choices, 
                                                  beta=self.stability)]

        if verbose:
            print(next_event["name"])
        self.log.append(next_event["name"])
        self.execute_event(next_event)
        self.store_state()

    def run(self, n_steps=20, verbose=True):
        '''
        Keep advancing events for a set number of steps, or until termination.

        Args:
            n_steps: Maximum number of steps to run for.
            verbose: If True, print the name of each event; if "Full", print
                     the possible events at each step before one is chosen; if
                     False, do not print anything.
        '''
        for _ in range(n_steps):
            self.advance(verbose)
            if not self.running:
                break

    def store_state(self):
        '''
        Create a static copy of the current state and append it to the history.
        '''

        frozen_state = {}
        for tag, values in self.state.items():
            if len(values) > 0:
                frozen_state[tag] = list(values)
        self.state_history.append(frozen_state)


    @staticmethod
    def weighted_random(choices, exp=True, beta=1.0):
        '''
        Pick a key at random from a dictionary where values are weights.`

        Args:
            choices: A dictionary mapping keys to real-numbered weights
            exp: If True, exponentiate all the weights. Note: If False, all
                 weights must be positive.
            beta: Multiply all weights by this factor before exponentiating.
                  When 0, makes all weights equal; large numbers make small
                  weight differences increasingly likely.

        Returns:
            One of the keys, chosen at random.
        '''

        if exp:
            choices = {key: math.exp(beta * val) 
                       for key, val in choices.items()}
        total = sum([v for v in choices.values()])
        target = random.random() * total
        counter = 0
        for k, v in choices.items():
            if counter + v >= target:
                return k
            counter += v
        else:
            raise Exception("Shouldn't be here")

    # ====================================
    # Diagnostics
    # ---------------------------------------------------------

    def validate_events(self, verbose=True):
        '''
        Make sure that all event dictionaries are correctly formatted.

        Args:
            verbose: If True, print the details of each misformatted event.

        Returns:
            True if all events are valid, otherwise False.
        '''
        all_valid = True
        out_template = "{}\n\tMissing keys: {}\n"
        for event in self.events:
            validation = self._validate_event(event)
            if not validation["valid"]:
                all_valid = False
                if verbose:
                    print(out_template.format(event, validation["missing"]))
        return all_valid

    @staticmethod
    def _validate_event(event):
        '''
        Check whether an event is valid.

        Args:
            event: An event object.

        Returns:
            A dictionary with the form 
            {"valid": True if the event is valid, otherwise False,
            "missing": [A list of required keys missing from the event],
            "additional": [A list of unrecognized keys found in the event]}
        '''
        mandatory_keys = ["name", "preconditions", "effects"]
        optional_keys = ["influences", "weights"]
        validation = {"valid": True, 
                      "missing": [], 
                      "additional": []
                      }
        for key in mandatory_keys:
            if key not in event:
                validation["valid"] = False
                validation["missing"].append(key)
        for key in event:
            if key not in mandatory_keys + optional_keys:
                validation["additional"].append(key)
        return validation


    def get_possible_tags(self):
        '''
        Get all possible labels for all possible tags.

        Loop through all events, and aggregate all the effects.

        Returns:
            A dictionary mapping tags to all possible labels that event effects
            can cause.
        '''
        possible_tags = defaultdict(set)
        for event in self.events:
            for tag, labels in event["effects"].items():
                labels = [label.strip() for label in labels.split(";")]
                for label in labels:
                    if len(label) == 0: continue
                    if label[0] in ["-", "+"]:
                        label = label[1:]
                    possible_tags[tag].add(label)
        return dict(possible_tags)

    @staticmethod
    def make_template(event_names, file_path, all_keys=False):
        '''
        Write a JSON file with a grammar template with event names pre-filled.

        Args:
            event_names: A list of event names to fill the template with.
            file_path: File output path
            all_keys: If False, only fill the template with "name", "preconditions"
                      and "effects"; if True, also add "weight" and "influences"
        '''

        event_list = []
        for name in event_names:
            event = {}
            event["name"] = name
            event["preconditions"] = {}
            event["effects"] = {}
            if all_keys:
                event["influences"] = {}
                event["weight"] = 0

            event_list.append(event)
        data = {"events": event_list}
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
