# Architecture and decisions

`schema.py` owns version/field/order validation and canonical serialization. `engine.py` owns only the three deterministic example policies. `scoring.py` reconstructs expected eligibility from recorded scenario inputs and evaluates observed actions independently of policy code. `report.py` presents escaped traces without network assets; `cli.py` composes these parts and exports artifacts.

The first version uses Python standard library only. No transport, cloud account, LLM model, private Core or simulator is needed to reproduce it. Both contexts share the event contract because the initial question concerns interaction-state transitions, not mechanics or patient realism.

The faulty policy is a negative fixture, never a recommended controller. The always-stop policy guards against conflating inactivity with useful behavior. Independent scoring accepts external policy traces but v1 is a narrow authored-event contract, not open-world language evaluation or a validated HRI benchmark.

ROS 2 integration must be tested separately through a supported event/status topic round-trip. A future adapter must never silently translate OFFER into motor commands. Gazebo/VR are deferred until sensing, geometry or immersion is a required experimental variable.

Public/private boundary: this repository starts with new independent source and history. No UniversalMind Core files, datasets, accounts or history are reused. License selection belongs to Iman; no VetoLatch license is inherited.
