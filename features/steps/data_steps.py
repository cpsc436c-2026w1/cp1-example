"""Steps that put data in front of the system: a table inside the example, or a simulated data set by its id.

A data set is read as the system receives it: the files of sim/data/<id>/ outside _truth/ (sim/generate.py,
load_received). SIM05 is not committed (42,797 files): the first example that names it writes it, with the same seed.
"""
from behave import given

from sim.datasets import DATA_SETS
from sim.generate import generate, is_written, load_received


@given("only these trip requests are received:")
def step_requests_table(context):
    for row in context.table:
        delivery = dict(zip(context.table.headings, row.cells))
        delivery["event_type"] = "trip_requested"
        context.deliveries.append(delivery)


@given('the simulated data set {sim_id} "{name}"')
def step_data_set(context, sim_id, name):
    assert sim_id in DATA_SETS, f"{sim_id} is not a data set in sim/datasets.py"
    assert DATA_SETS[sim_id]["name"] == name, f'{sim_id} is named "{DATA_SETS[sim_id]["name"]}", not "{name}"'
    if not is_written(sim_id):
        generate(sim_id)                                  # SIM05: written on first use
    context.data_set_id = sim_id
    if DATA_SETS[sim_id]["kind"] != "minute files":       # SIM05 is read from its files by the steps that use it
        if sim_id not in context.received:
            context.received[sim_id] = load_received(sim_id)
        context.deliveries = list(context.received[sim_id])
