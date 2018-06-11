# MainSequence (working title)

MainSequence is a generative system. The purpose of MainSequence is to generate random, plausible sequences of events based on an event ruleset. Events modify the world state, which in turn determines which events might happen next. Both events and world-states are defined using JSON-able objects (aka Python dictionaries).

**TODO:** The actual text generation system. In theory, text can be generated to describe the current world state, and/or to describe the sequence of events leading to it.

MainSequence is influenced by [Tracery](https://github.com/galaxykate/tracery), [Improv](https://github.com/sequitur/improv), and [cross-imact analysis](https://en.wikipedia.org/wiki/Cross_impact_analysis).

#### Motivating example

MainSequence is initially being developed as part of *Lighthugger*, a space trading and exploration game intended to feature procedurally-generated colonies where the player's actions have a real impact on the colonies' development. MainSequence is intended to allow for random colony histories (resulting in different goods and services); for the players to have delayed information about the colonies (if a colony is 30 light-years away, the information available is 30 years out of date); and for the players' decisions to actually change the trajectory of a colony's future.

## How to use

To generate event sequences using the example models, in this directory:

```
>>> from mainsequence import EventModel
>>> model = EventModel("rulesets/planet.json")
>>> model.run(5)
extreme storm
First landing
first settlement grows
more small settlements
university established
```

```
>>> from mainsequence import EventModel
>>> model = EventModel("rulesets/bank_heist.json", repeating_events=False)
>>> model.run()
Crew pulls up
Crew walks into the bank
Crew pull out guns
Tellers hand over the money
Police show up
Crew arrested
```

Event rulesets are defined in a JSON file with the following structure:

```
{
	"events": [
		// A list of events:
		{
			"name": "An event name",
			"preconditions": {"tag": "labels", ...},
			"effects": {"tag": "label changes", ...},
			"weight": optional numeric probability weight,
			"influences": {"optional tag": {"label": influence}}
		},
		...
	],
	"starting_state": 
		// Optional initial state object; defaults to {}
		{
			"a tag": ["label", "another label"],
			"another tag": ["a label"]
		}
}
``` 

For details on what that all means, keep reading.

## World State

A world state is defined by tags and labels. Tags are categories of facts or attributes about the world, while labels are specifc facts or attributes that are true at the moment. Both tags and labels are strings; each tag is associated with a list of labels. 

For example, an early state of a colony might be:

```.json
{
	"settlement": ["First landing site"],
	"government": ["Unified"]
}
```

A later state might be:

```.json
{
	"settlement": ["Capital city", "Many cities", "Factory farms"],
	"government": ["City states"],
	"international relations": ["Simmering tensions"],
	"economy": ["Stagnant"],
	"university": ["Biotech research", "Student radicals"]
}
```
## Events

Events are randomly chosen based on the current world state, and modify the world state. Each event has at a minimum three mandatory properties: `"name"`, `"preconditions"`, and `"effects"`. The name is simply a unique identifier string. `"preconditions"` is a nested dictionary of tags to labels: all those tags must have all those labels in the current world state for an event to occur. Finally, `"effects"` is another dictionary, mapping tags to labels to update in the world state. Both preconditions and effects have some special syntax, which will be described more below.

Here's the simplest possible event:

```.json
{
	"name": "Asteroid impact",
	"preconditions": {},
	"effects": {"craters": "Asteroid crater"}
}
```

This event has no preconditions (meaning it can occur at any time), and it updates the `"craters"` tag to have the value "Asteroid crater".

World state before:
```.json
{

}
```

Then `"Asteroid impact"` occurs.

```.json
{
	"craters": ["Asteroid crater"]
}
```

Of course, usually you only want an event to happen if certain preconditions are met. For example, suppose the history of a colony must always start with a first landing. Once that happens, the initial settlement might grow into a bigger city; more small settlements might be founded. There might also be an early political schism, but only if the initial settlement hasn't grown into a city yet.

Here is that written in the event syntax:

```.json
[
{
	"name": "First landing",
	"preconditions": {"settlement": "!"},
	"effects": {
		"settlement": "First landing site", 
		"government": "Unified"
	}
},
{
	"name": "More small settlements",
	"preconditions": {"settlement": "*"},
	"effects": {"settlement": "+small settlements"}
},
{
	"name": "First settlement grows",
	"preconditions": {"settlement": "First landing site"},
	"effects": {"settlement": "-First landing site; +Capital city"}
},
{
	"name": "Early schism",
	"preconditions": {
		"settlement": "First landing site", 
		"government": "Unified"
	},
	"effects": {"government": "Divided"}
}
]
```


This example also introduces some of the special syntax in defining events. The precondition for `"First landing"` is `{"settlement": "!"}` -- the `!` means that the precondition is that there be no labels at all associated with the `"settlement"` tag (this ensures the event can happen only once). That event sets the `"settlement"` tag to `"First landing site"` (so the first landing can't happen again), and sets `"government"`` to `"Unified"`.

The precondition for `"More small settlements"` is `{"settlement": "*"}`. The `*` is the opposite of `!` -- it means the requirement is that there be any label at all under the `"settlement"` tag. The effect, `{"settlement": "+small settlements"}` means *Add the label "small settlements" to the "settlement" tag*. The plus `+` sign at the beginning of the label means *append* as opposed to the default *replace*.

Next, `First settlement grows` can only happen once the first landing site has been established. It has two effects operating on the same tag, divided by a semi-colon `;`. The minus `-` at the beginning of `-First landing site` means **remove** the label `"First landing site"` from the `"settlement"` tag. Then, as above, the `+` sign appends a label. Together, this can be read as *replace the "First settlement" label with the "Capital city" label*. 

Finally, `"Early schism"` has two preconditions: that the `"First landing site"` label still be under `"settlement"` (meaning that it cannot occur if the `"First settlement grows"` event has already happened); that the `"government"` be `"Unified"` -- which in this case, means that this event can't happen more than once.

### Weights and influence

In many cases, we want different events to have different probabilities of happening; two events may both be possible, but one might be more likely than the other. Different world states may may some events more or less likely. For example, a `rain` event may happen at any time of year, but is more likely for `{"season": "rainy season"}` than `{"season": "dry season"}`. 

To understand weights and influences, we need to mention how MainSequence does probabilities. Each event is assigned a `weight` property -- if no weight is explicitly given, it defaults to 0. If we write the weight of a certain event $x_i$ as $w_i$, then:

$$ P(x_{t+1}=x_i) = \frac{e^{\beta*w_i}}{\sum_j e^{\beta*w_j}} $$

($\beta$ is a parameter controlling how much small differences in weights matter; $\beta=1$ means that all events have the same probaibity regardless of weights; higher $\beta$ means that the highest-weighted event is increasingly certain to be chosen; by default, $\beta=1$).

If all weights are the same, that means all events have the same probability of being chosen. Raising a weight by 1 roughly doubles the probability; reducing by one roughly halves it. 

**Sidebar:** Why are we exponentiating, instead of just summing the weights themselves? Two reasons: **(1)** This lets us use negative weights, so we can reduce weights below 0 without anything breaking, and **(2)** adds in the $\beta$ parameter, which allows us to make unlikely events increasingly possible.

To directly assign a weight to an event, explicitly give it a `"weight"` property. For example, an unlikely earthquake that could happen at any time might be:

```.json
{
	"name": "Earthquake",
	"preconditions": {},
	"weight": -2,
	"effects": {"really bad stuff": "true"}
}
```

***Influences*** are tag-label combinations in the world state that change the probability weight associated with an event. They're written as nested dictionaries, with the form `{"tag": {"label 1": change, "label 2": change}`. The labels follow the same format as preconditions: if it is a plain label, it checks whether the label is present for that tag, and if so applies the change. A `"*"` means that if there is *any* label associated with the tag; `"!"` checks that there is no label associated with the tag; and `"!label"` checks whether there is any label except the listed one. 

For example, suppose terraforming a planet makes earthquakes more likely, but geoengineering technology can mitigate that. The event could be:


```.json
{
	"name": "Earthquake",
	"preconditions": {},
	"weight": -2,
	"effects": {"really bad stuff": "true"},
	"influences": {"terraforming": {"*": 1.5}, "technology": {"geoengineering": -1}}
}
```

If the world state includes any labels under the `"terraforming"` tag, the weight on Earthquake is -2 + 1.5 = 0.5; however, if the world state includes

```.json
{
	"other tags": ["go here"],
	"terraforming": ["atmosphere stabilization", "oceans introduced"],
	"technology": ["gene editing", "high-temperature superconductors", "geoengineering"]
}
```

Then the total weight on Earthquakes is -2 + 1.5 - 1 = -1.5.


## Some application ideas

#### Generate stories

Define a set of possible events and use them to generate consistent stories. Stories will probably have `repeating_events=False`, and have one or more `"<END>"` effects to terminate the story.

#### Generate histories

Define a set of possible historic events, and simulate possible histories. Unlike stories, histories don't necessarily `"<END>"`. 

#### Forecasting and simulation

The MainSequence model is partially inspired by cross-impact analaysis, a methodology originally developed for forecasting and intelligence analysis. There's no reason a model can't describe potential real-world events and their relationships as estimated by experts, in which case the model can generate plausible ranges of predictions.

#### Time travel games and stories

Run a model forward; then rewind it to a past state, and run it forward from that point to create stories or games that explore how changing a point in the past can change the future.

## TODO

Possible features to implement

- **Unique:** Allow individual events to be tagged as one-time-only or repeating
- **Combiner preconditions:** Allow preconditions to be more complicated boolean combinations of tag labels
	+ Pro: Enable richer event graphs
	+ Con: Preserve the simplicity of the current system; 'or' relationships can be hacked around by creating two events with different preconditions and the same effects. 
- **Probabilistic effects:** allow one event to have several possible sets of effects, chosen at random. 
- **Variables!**


