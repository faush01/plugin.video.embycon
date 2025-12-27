from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


# --- Data Classes for Nested JSON Structure ---
@dataclass
class MediaStream:
    Title: Optional[str] = None
    Codec: Optional[str] = None
    Language: Optional[str] = None
    TimeBase: Optional[str] = None
    VideoRange: Optional[str] = None
    DisplayTitle: Optional[str] = None
    DisplayLanguage: Optional[str] = None
    NalLengthSize: Optional[str] = None
    IsInterlaced: Optional[bool] = None
    BitRate: Optional[int] = None
    BitDepth: Optional[int] = None
    RefFrames: Optional[int] = None
    IsDefault: Optional[bool] = None
    IsForced: Optional[bool] = None
    IsHearingImpaired: Optional[bool] = None
    Height: Optional[int] = None
    Width: Optional[int] = None
    AverageFrameRate: Optional[float] = None
    RealFrameRate: Optional[float] = None
    Profile: Optional[str] = None
    Type: Optional[str] = None
    AspectRatio: Optional[str] = None
    Index: Optional[int] = None
    IsExternal: Optional[bool] = None
    IsTextSubtitleStream: Optional[bool] = None
    SupportsExternalStream: Optional[bool] = None
    Protocol: Optional[str] = None
    PixelFormat: Optional[str] = None
    Level: Optional[int] = None
    IsAnamorphic: Optional[bool] = None
    ExtendedVideoType: Optional[str] = None
    ExtendedVideoSubType: Optional[str] = None
    ExtendedVideoSubTypeDescription: Optional[str] = None
    AttachmentSize: Optional[int] = None
    SubtitleLocationType: Optional[str] = None
    ChannelLayout: Optional[str] = None
    Channels: Optional[int] = None
    SampleRate: Optional[int] = None
    ColorTransfer: Optional[str] = None
    ColorPrimaries: Optional[str] = None
    ColorSpace: Optional[str] = None
    CodecTag: Optional[str] = None


@dataclass
class MediaSource:
    Protocol: str
    Id: str
    Path: str
    Type: str
    Container: str
    Size: int
    Name: Optional[str] = None
    IsRemote: Optional[bool] = None
    HasMixedProtocols: Optional[bool] = None
    RunTimeTicks: Optional[int] = None
    SupportsTranscoding: Optional[bool] = None
    SupportsDirectStream: Optional[bool] = None
    SupportsDirectPlay: Optional[bool] = None
    IsInfiniteStream: Optional[bool] = None
    RequiresOpening: Optional[bool] = None
    RequiresClosing: Optional[bool] = None
    RequiresLooping: Optional[bool] = None
    SupportsProbing: Optional[bool] = None
    MediaStreams: List[MediaStream] = field(default_factory=list)
    Formats: List[Any] = field(default_factory=list)
    Bitrate: Optional[int] = None
    RequiredHttpHeaders: Optional[Dict[str, Any]] = field(default_factory=dict)
    AddApiKeyToDirectStreamUrl: Optional[bool] = None
    ReadAtNativeFramerate: Optional[bool] = None
    DefaultAudioStreamIndex: Optional[int] = None
    ItemId: Optional[str] = None


@dataclass
class Studio:
    Name: str
    Id: int


@dataclass
class GenreItem:
    Name: str
    Id: int


@dataclass
class UserData:
    PlaybackPositionTicks: int
    PlayedPercentage: Optional[float] = 0.0
    UnplayedItemCount: Optional[int] = 0
    PlayCount: Optional[int] = 0
    IsFavorite: bool = False
    Played: bool = False


@dataclass
class TagItem:
    Name: str
    Id: int


@dataclass
class ImageTags:
    Primary: Optional[str] = None
    Thumb: Optional[str] = None
    Logo: Optional[str] = None
    Banner: Optional[str] = None
    Art: Optional[str] = None
    Disc: Optional[str] = None


@dataclass
class ProviderIds:
    Imdb: Optional[str] = None
    Tmdb: Optional[str] = None
    Tvdb: Optional[str] = None
    TvRage: Optional[str] = None


@dataclass
class Item:
    Name: str
    ServerId: str
    Id: str
    Etag: str
    DateCreated: str
    Guid: Optional[str] = None
    Container: Optional[str] = None
    SortName: Optional[str] = None
    PremiereDate: Optional[str] = None
    MediaSources: List[MediaSource] = field(default_factory=list)
    CriticRating: Optional[int] = None
    ProductionLocations: List[str] = field(default_factory=list)
    Path: Optional[str] = None
    OfficialRating: Optional[str] = None
    Overview: Optional[str] = None
    Taglines: List[str] = field(default_factory=list)
    Genres: List[str] = field(default_factory=list)
    CommunityRating: Optional[float] = None
    RunTimeTicks: Optional[int] = None
    Size: Optional[int] = None
    Bitrate: Optional[int] = None
    ProductionYear: Optional[int] = None
    IsFolder: Optional[bool] = None
    Type: Optional[str] = None
    Studios: List[Studio] = field(default_factory=list)
    GenreItems: List[GenreItem] = field(default_factory=list)
    TagItems: List[TagItem] = field(default_factory=list)
    UserData: Optional[UserData] = None  # type: ignore
    MediaStreams: List[MediaStream] = field(default_factory=list)
    ImageTags: Optional[ImageTags] = None  # type: ignore
    BackdropImageTags: List[str] = field(default_factory=list)
    MediaType: Optional[str] = None
    CanDelete: Optional[bool] = None
    CanDownload: Optional[bool] = None
    PresentationUniqueKey: Optional[str] = None
    ForcedSortName: Optional[str] = None
    ExternalUrls: List[str] = field(default_factory=list)
    RemoteTrailers: List[str] = field(default_factory=list)
    ProviderIds: Optional[Dict[str, str]] = field(default_factory=dict)
    ParentId: Optional[str] = None
    ChildCount: Optional[int] = None
    DisplayPreferencesId: Optional[str] = None
    PrimaryImageAspectRatio: Optional[float] = None
    CollectionType: Optional[str] = None
    LockedFields: Optional[List[str]] = field(default_factory=list)
    LockData: Optional[bool] = None
    RecursiveItemCount: Optional[int] = None
    Status: Optional[str] = None
    AirDays: List[str] = field(default_factory=list)
    IndexNumber: Optional[int] = None
    ParentLogoItemId: Optional[str] = None
    ParentBackdropItemId: Optional[str] = None
    ParentBackdropImageTags: Optional[List[str]] = field(default_factory=list)
    SeriesName: Optional[str] = None
    SeriesId: Optional[str] = None
    SeriesPrimaryImageTag: Optional[str] = None
    ParentLogoImageTag: Optional[str] = None
    ParentThumbItemId: Optional[str] = None
    ParentThumbImageTag: Optional[str] = None
    ParentIndexNumber: Optional[int] = None
    SeasonId: Optional[str] = None
    SeasonName: Optional[str] = None


@dataclass
class DataSet:
    Items: List[Item]
