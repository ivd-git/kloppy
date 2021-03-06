# from kloppy.domain import TrackingDataSet, EventDataSet, PitchDimensions, Dimension, Orientation, DataSetFlag, Period, \
#     Frame, TrackingPossessionEnricher, SetPieceEvent, BallState, Team
#
#
# class TestEnricher:
#     def test_enrich_tracking_data(self):
#         periods = [
#             Period(id=1, start_timestamp=0.0, end_timestamp=10.0),
#             Period(id=2, start_timestamp=15.0, end_timestamp=25.0)
#         ]
#         tracking_data = TrackingDataSet(
#             flags=~(DataSetFlag.BALL_OWNING_TEAM | DataSetFlag.BALL_STATE),
#             pitch_dimensions=PitchDimensions(
#                 x_dim=Dimension(0, 100),
#                 y_dim=Dimension(-50, 50)
#             ),
#             orientation=Orientation.HOME_TEAM,
#             frame_rate=25,
#             records=[
#                 Frame(
#                     frame_id=1,
#                     timestamp=0.1,
#                     ball_owning_team=None,
#                     ball_state=None,
#                     period=periods[0],
#
#                     away_team_player_positions={},
#                     home_team_player_positions={},
#                     ball_position=None
#                 )
#             ],
#             periods=periods
#         )
#
#         event_data = EventDataSet(
#             flags=DataSetFlag.BALL_OWNING_TEAM | DataSetFlag.BALL_STATE,
#             pitch_dimensions=PitchDimensions(
#                 x_dim=Dimension(0, 100),
#                 y_dim=Dimension(-50, 50)
#             ),
#             orientation=Orientation.HOME_TEAM,
#             records=[
#                 # SetPieceEvent(
#                 #     event_id=1,
#                 #     timestamp=0.1,
#                 #     ball_owning_team=Team.HOME,
#                 #     ball_state=BallState.ALIVE,
#                 #     period=periods[0],
#                 #     team=Team.HOME,
#                 # )
#             ],
#             periods=periods
#         )
#
#         enricher = TrackingPossessionEnricher()
#         enricher.enrich_inplace(
#             tracking_data_set=tracking_data,
#             event_data_set=event_data
#         )