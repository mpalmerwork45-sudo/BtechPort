"""Event navigation remains finite and complete with loops and islands."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from event_workbench import graph_arrangement,graph_neighbours


class GraphTests(unittest.TestCase):
    def test_cycles_and_disconnected_events(self):
        events=[dict(id='a',op='say',next='b'),dict(id='b',op='choice',options=[dict(label='Again',next='a'),dict(label='Exit',next='c')]),dict(id='c',op='end'),dict(id='island',op='end')]
        positions=graph_arrangement(events)
        self.assertEqual(set(positions),{'a','b','c','island'})
        self.assertEqual(len({tuple(p) for p in positions.values()}),4)
        self.assertEqual(graph_neighbours(events,'b'),{'a','b','c'})
        self.assertEqual(positions,graph_arrangement(events))

    def test_nearby_filter_keeps_predecessors_without_entire_campaign(self):
        events=[dict(id=str(i),op='say',next=str(i+1)) for i in range(8)]+[dict(id='8',op='end')]
        self.assertEqual(graph_neighbours(events,'3'),{'2','3','4','5'})
