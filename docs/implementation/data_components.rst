Data Components
===============

A data component represents the common functionality between
State Managers and Consumers. It handles connecting to the broker
and managing the event loop.

Every standalone application in Astoria must be a Data Component.

The entrypoint of any data component is the ``run`` function.
