@JS04 @assistant
Feature: Pickup place of a rider's message
  Covers JS04 (support agent) in a system that includes the assistant, our extension. The assistant sends the
  rider's message to the model as the user message; the output format is a JSON object with one field,
  pickup_place: a name from evals/pickup_place/places.txt, null when the message names no pickup place, or
  "more than one" when it names more than one.
  The replies are recorded examples written by hand (evals/pickup_place/), not a model run: the examples check the
  checker and what the page shows, not the model.

  @R110
  Rule: Where the system includes the assistant, when a support agent opens a rider's message, the system shall show the pickup place that the message names, as a name from our list of places, or say that the message names no pickup place

    Example: Message that names a pickup place
      Given the rider message "I'm waiting outside JFK Terminal 4, door 6. Where is my driver?"
      When the support agent opens the message
      Then the pickup place is "JFK Terminal 4"

    Example: Message that names only a destination
      Given the rider message "Take me to Penn Station. I haven't decided where to be picked up yet."
      When the support agent opens the message
      Then the system says that the message names no pickup place

    @eval
    Example: Eval of pickup places
      Given the 10 cases of the eval "pickup-place"
      When the model that the system uses answers each case 3 times
      Then the pickup place is correct in at least 24 of the 30 runs

  @R120
  Rule: If a rider's message names more than one pickup place, then the system shall say that the message names more than one pickup place, and not show any of them as the pickup place

    Example: Message that names two pickup places
      Given the rider message "Pick me up at Penn Station or at Grand Central Terminal, whichever is faster for the driver."
      When the support agent opens the message
      Then the system says that the message names more than one pickup place
