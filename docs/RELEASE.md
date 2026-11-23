# Release procedure and current blockers

Iman Khorami explicitly approved Apache-2.0 on 2026-11-23. LICENSE contains the official Apache text; NOTICE identifies the owner. This approval applies to RelatioBench only.

Current private repository: https://github.com/ImanCognitiveArch/relatiobench . Repository existence is not a public release. Core source initial verification commit: `9f7311116be07461bedc954bca42c6cc1a6745df`.

Before public release:

1. Record the chosen license, include its complete text and consistent package metadata; review the public files and independent history.
2. Rebuild wheel/sdist and verify archive contents, `twine check`, tests and fresh installation. Record final SHA256; a previous build's hash does not describe a new build.
3. Tag the reviewed commit with the actual alpha version. Create a release containing the distributions and reproduction resources.
4. Set scoped Trusted Publishers on TestPyPI/PyPI: owner `ImanCognitiveArch`, repository `relatiobench`, workflow `publish.yml`, environment `testpypi` or `pypi`. Only configure the package and repository within this task's authority. Account authentication/verification stays under the owner's control; never commit credentials.
5. Run the manual publishing workflow for TestPyPI first if access permits, then `pypi`. An absent publisher/account is a concrete blocker, not grounds to claim a published package or use another project's token.
6. After success, verify the actual registry version and install from the public index in a fresh environment. Update README public commands and status using observed evidence.
7. Publish accurate release/demo links in the authorized channels; deduplicate external invitations before sending.

ROS integration is separate: no `rclpy` was found in the inspected Linux Python or Windows Python 3.11, and no `ros2` command was found on the inspected Windows PATH. A supported, sourced ROS environment and real pub/sub test are required before claiming integration. These checks do not prove that no alternate ROS installation exists anywhere on the device.

Direct file-tool access to `D:\RelatioBench` was denied by its configured allowed-directory list at build start. Build proceeded in the authorized independent workspace; Windows clean-install evidence lives under `D:\Research-Portfolio\RelatioBench-release-20261123`. Do not claim that updated source was delivered to `D:\RelatioBench` until permitted and verified.

Browser rendering of the local file was blocked by the browser URL policy. The report is generated and structurally checked; visual browser inspection remains unverified. A CLI-session recording is separate evidence, not a substitute claim that the graphical report was browser-tested.
