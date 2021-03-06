from collections import namedtuple
from typing import Tuple, Dict, Iterator

from kloppy.domain import (attacking_direction_from_frame,
                           TrackingDataSet,
                           AttackingDirection,
                           Frame,
                           Point,
                           Period,
                           Orientation,
                           PitchDimensions,
                           Dimension,
                           DataSetFlag)
from kloppy.infra.utils import Readable, performance_logging

from . import TrackingDataSerializer


class MetricaTrackingSerializer(TrackingDataSerializer):
    __PartialFrame = namedtuple("PartialFrame", "team period frame_id player_positions ball_position")

    @staticmethod
    def __validate_inputs(inputs: Dict[str, Readable]):
        if "raw_data_home" not in inputs:
            raise ValueError("Please specify a value for input 'raw_data_home'")
        if "raw_data_away" not in inputs:
            raise ValueError("Please specify a value for input 'raw_data_away'")

    def __create_iterator(self, data: Readable, sample_rate: float, frame_rate: int) -> Iterator:
        """
        Notes:
            1. the y-axis is flipped because Metrica use (y, -y) instead of (-y, y)
        """

        team = None
        frame_idx = 0
        frame_sample = 1 / sample_rate
        player_jersey_numbers = []
        period = None

        for i, line in enumerate(data):
            line = line.strip().decode('ascii')
            columns = line.split(',')
            if i == 0:
                team = columns[3]
            elif i == 1:
                player_jersey_numbers = columns[3:-2:2]
            elif i == 2:
                # consider doing some validation on the columns
                pass
            else:
                period_id = int(columns[0])
                frame_id = int(columns[1])

                if period is None or period.id != period_id:
                    period = Period(
                        id=period_id,
                        start_timestamp=frame_id / frame_rate,
                        end_timestamp=frame_id / frame_rate
                    )
                else:
                    # consider not update this every frame for performance reasons
                    period.end_timestamp = frame_id / frame_rate

                if frame_idx % frame_sample == 0:
                    yield self.__PartialFrame(
                        team=team,
                        period=period,
                        frame_id=frame_id,
                        player_positions={
                            player_no: Point(
                                x=float(columns[3 + i * 2]),
                                y=1 - float(columns[3 + i * 2 + 1])
                            )
                            for i, player_no in enumerate(player_jersey_numbers)
                            if columns[3 + i * 2] != 'NaN'
                        },
                        ball_position=Point(
                            x=float(columns[-2]),
                            y=1 - float(columns[-1])
                        ) if columns[-2] != 'NaN' else None
                    )
                frame_idx += 1

    @staticmethod
    def __validate_partials(home_partial_frame: __PartialFrame, away_partial_frame: __PartialFrame):

        if home_partial_frame.frame_id != away_partial_frame.frame_id:
            raise ValueError(f"frame_id mismatch: home {home_partial_frame.frame_id}, "
                             f"away: {away_partial_frame.frame_id}")
        if home_partial_frame.ball_position != away_partial_frame.ball_position:
            raise ValueError(f"ball position mismatch: home {home_partial_frame.ball_position}, "
                             f"away: {away_partial_frame.ball_position}. Do the files belong to the"
                             f" same game? frame_id: {home_partial_frame.frame_id}")
        if home_partial_frame.team != 'Home':
            raise ValueError("raw_data_home contains away team data")
        if away_partial_frame.team != 'Away':
            raise ValueError("raw_data_away contains home team data")

    def deserialize(self, inputs: Dict[str, Readable], options: Dict = None) -> TrackingDataSet:
        """
        Deserialize Metrica tracking data into a `TrackingDataSet`.

        Parameters
        ----------
        inputs : dict
            input `raw_data_home` should point to a `Readable` object containing
            the 'csv' formatted raw data for the home team. input `raw_data_away` should point
            to a `Readable` object containing the 'csv' formatted raw data for the away team.
        options : dict
            Options for deserialization of the Metrica file. Possible options are
            `sample_rate` (float between 0 and 1) to specify the amount of
            frames that should be loaded, `limit` to specify the max number of
            frames that will be returned.
        Returns
        -------
        data_set : TrackingDataSet
        Raises
        ------
        ValueError when both input files don't seem to belong to each other

        See Also
        --------

        Examples
        --------
        >>> serializer = MetricaTrackingSerializer()
        >>> with open("Sample_Game_1_RawTrackingData_Away_Team.csv", "rb") as raw_home, \
        >>>      open("Sample_Game_1_RawTrackingData_Home_Team.csv", "rb") as raw_away:
        >>>
        >>>     data_set = serializer.deserialize(
        >>>         inputs={
        >>>             'raw_data_home': raw_home,
        >>>             'raw_data_away': raw_away
        >>>         },
        >>>         options={
        >>>             'sample_rate': 1/12
        >>>         }
        >>>     )
        """
        self.__validate_inputs(inputs)
        if not options:
            options = {}

        sample_rate = float(options.get('sample_rate', 1.0))
        limit = int(options.get('limit', 0))

        # consider reading this from data
        frame_rate = 25

        with performance_logging("prepare"):
            home_iterator = self.__create_iterator(inputs['raw_data_home'], sample_rate, frame_rate)
            away_iterator = self.__create_iterator(inputs['raw_data_away'], sample_rate, frame_rate)

            partial_frames = zip(home_iterator, away_iterator)

        with performance_logging("loading"):
            frames = []
            periods = []

            partial_frame_type = self.__PartialFrame
            home_partial_frame: partial_frame_type
            away_partial_frame: partial_frame_type
            for n, (home_partial_frame, away_partial_frame) in enumerate(partial_frames):
                self.__validate_partials(home_partial_frame, away_partial_frame)

                period: Period = home_partial_frame.period
                frame_id: int = home_partial_frame.frame_id

                frame = Frame(
                    frame_id=frame_id,
                    timestamp=frame_id / frame_rate - period.start_timestamp,
                    ball_position=home_partial_frame.ball_position,
                    home_team_player_positions=home_partial_frame.player_positions,
                    away_team_player_positions=away_partial_frame.player_positions,
                    period=period,
                    ball_state=None,
                    ball_owning_team=None
                )

                frames.append(frame)

                if not periods or period.id != periods[-1].id:
                    periods.append(period)

                if not period.attacking_direction_set:
                    period.set_attacking_direction(
                        attacking_direction=attacking_direction_from_frame(frame)
                    )

                n += 1
                if limit and n >= limit:
                    break

        orientation = (
            Orientation.FIXED_HOME_AWAY
            if periods[0].attacking_direction == AttackingDirection.HOME_AWAY else
            Orientation.FIXED_AWAY_HOME
        )

        return TrackingDataSet(
            flags=~(DataSetFlag.BALL_STATE | DataSetFlag.BALL_OWNING_TEAM),
            frame_rate=frame_rate,
            orientation=orientation,
            pitch_dimensions=PitchDimensions(
                x_dim=Dimension(0, 1),
                y_dim=Dimension(0, 1)
            ),
            periods=periods,
            records=frames
        )

    def serialize(self, data_set: TrackingDataSet) -> Tuple[str, str]:
        raise NotImplementedError
