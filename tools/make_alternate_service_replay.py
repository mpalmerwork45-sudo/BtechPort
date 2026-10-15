#!/usr/bin/env python3
"""Ordinary garage, electronics refusals and repeat clothing visit from GAME3."""
from make_late_building_replays import Buildings
from make_fresh_campaign_replay import Fresh


class Visit(Fresh):
    # Share the ordinary garage checkout/parking inputs. No coordinates,
    # inventory, story flags, money or random seed are edited.
    def __init__(self,source,stem):
        Buildings.__init__(self,source,stem)


def main():
    s=Visit('GAME3','alternate-services');cash=s.state['credits']
    s.enter(1289,1045);s.note('electronics-menu')
    if s.state['menu_id']!=35:raise RuntimeError('Electronics menu unavailable')
    s.choose(0);s.note('electronics-products');s.choose(0);s.note('viewer-party-refusal')
    if s.state['menu_id']!=35:raise RuntimeError('Viewer refusal did not return to the shop')
    s.choose(0);s.choose(1);s.note('mapper-already-owned');s.choose(1)
    s.enter(1370,1088);s.note('clothing-already-owned')
    if s.state['mode']!='local-exploration' or s.state['credits']!=cash:
        raise RuntimeError('Repeat service visits changed money or failed to exit')
    s.save('alternate-services')


if __name__=='__main__':main()
