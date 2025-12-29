from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any


# --- Data Classes for Nested JSON Structure ---
@dataclass
class MediaStream:
    Title: str | None = None
    Codec: str | None = None
    Language: str | None = None
    TimeBase: str | None = None
    VideoRange: str | None = None
    DisplayTitle: str | None = None
    DisplayLanguage: str | None = None
    NalLengthSize: str | None = None
    IsInterlaced: bool | None = None
    BitRate: int | None = None
    BitDepth: int | None = None
    RefFrames: int | None = None
    IsDefault: bool | None = None
    IsForced: bool | None = None
    IsHearingImpaired: bool | None = None
    Height: int | None = None
    Width: int | None = None
    AverageFrameRate: float | None = None
    RealFrameRate: float | None = None
    Profile: str | None = None
    Type: str | None = None
    AspectRatio: str | None = None
    Index: int | None = None
    IsExternal: bool | None = None
    IsTextSubtitleStream: bool | None = None
    SupportsExternalStream: bool | None = None
    Protocol: str | None = None
    PixelFormat: str | None = None
    Level: int | None = None
    IsAnamorphic: bool | None = None
    ExtendedVideoType: str | None = None
    ExtendedVideoSubType: str | None = None
    ExtendedVideoSubTypeDescription: str | None = None
    AttachmentSize: int | None = None
    SubtitleLocationType: str | None = None
    ChannelLayout: str | None = None
    Channels: int | None = None
    SampleRate: int | None = None
    ColorTransfer: str | None = None
    ColorPrimaries: str | None = None
    ColorSpace: str | None = None
    CodecTag: str | None = None
    Path: str | None = None
    MimeType: str | None = None


@dataclass
class MediaSource:
    Protocol: str
    Id: str
    Path: str
    Type: str
    Container: str
    Size: int
    Name: str | None = None
    IsRemote: bool | None = None
    HasMixedProtocols: bool | None = None
    RunTimeTicks: int | None = None
    SupportsTranscoding: bool | None = None
    SupportsDirectStream: bool | None = None
    SupportsDirectPlay: bool | None = None
    IsInfiniteStream: bool | None = None
    RequiresOpening: bool | None = None
    RequiresClosing: bool | None = None
    RequiresLooping: bool | None = None
    SupportsProbing: bool | None = None
    MediaStreams: List[MediaStream] = field(default_factory=list)
    Formats: List[Any] = field(default_factory=list)
    Bitrate: int | None = None
    RequiredHttpHeaders: Dict[str, Any] | None = field(default_factory=dict)
    AddApiKeyToDirectStreamUrl: bool | None = None
    ReadAtNativeFramerate: bool | None = None
    DefaultAudioStreamIndex: int | None = None
    ItemId: str | None = None
    Chapters: List[Any] = field(default_factory=list)
    DefaultSubtitleStreamIndex: int | None = None


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
    PlayedPercentage: float | None = 0.0
    UnplayedItemCount: int | None = 0
    PlayCount: int | None = 0
    IsFavorite: bool = False
    Played: bool = False


@dataclass
class TagItem:
    Name: str
    Id: int


@dataclass
class ImageTags:
    Primary: str | None = None
    Thumb: str | None = None
    Logo: str | None = None
    Banner: str | None = None
    Art: str | None = None
    Disc: str | None = None


@dataclass
class ProviderIds:
    Imdb: str | None = None
    Tmdb: str | None = None
    Tvdb: str | None = None
    TvRage: str | None = None


@dataclass
class Item:
    Name: str
    ServerId: str
    Id: str
    Etag: str
    DateCreated: str
    Guid: str | None = None
    Container: str | None = None
    SortName: str | None = None
    PremiereDate: str | None = None
    MediaSources: List[MediaSource] = field(default_factory=list)
    CriticRating: int | None = None
    ProductionLocations: List[str] = field(default_factory=list)
    Path: str | None = None
    OfficialRating: str | None = None
    Overview: str | None = None
    Taglines: List[str] = field(default_factory=list)
    Genres: List[str] = field(default_factory=list)
    CommunityRating: float | None = None
    RunTimeTicks: int | None = None
    Size: int | None = None
    Bitrate: int | None = None
    ProductionYear: int | None = None
    IsFolder: bool | None = None
    Type: str | None = None
    Studios: List[Studio] = field(default_factory=list)
    GenreItems: List[GenreItem] = field(default_factory=list)
    TagItems: List[TagItem] = field(default_factory=list)
    UserData: UserData | None = None  # type: ignore
    MediaStreams: List[MediaStream] = field(default_factory=list)
    ImageTags: ImageTags | None = None  # type: ignore
    BackdropImageTags: List[str] = field(default_factory=list)
    MediaType: str | None = None
    CanDelete: bool | None = None
    CanDownload: bool | None = None
    PresentationUniqueKey: str | None = None
    ForcedSortName: str | None = None
    ExternalUrls: List[str] = field(default_factory=list)
    RemoteTrailers: List[str] = field(default_factory=list)
    ProviderIds: Dict[str, str] | None = field(default_factory=dict)
    ParentId: str | None = None
    ChildCount: int | None = None
    DisplayPreferencesId: str | None = None
    PrimaryImageAspectRatio: float | None = None
    CollectionType: str | None = None
    LockedFields: List[str] | None = field(default_factory=list)
    LockData: bool | None = None
    RecursiveItemCount: int | None = None
    Status: str | None = None
    AirDays: List[str] = field(default_factory=list)
    IndexNumber: int | None = None
    ParentLogoItemId: str | None = None
    ParentBackdropItemId: str | None = None
    ParentBackdropImageTags: List[str] | None = field(default_factory=list)
    SeriesName: str | None = None
    SeriesId: str | None = None
    SeriesPrimaryImageTag: str | None = None
    ParentLogoImageTag: str | None = None
    ParentThumbItemId: str | None = None
    ParentThumbImageTag: str | None = None
    ParentIndexNumber: int | None = None
    SeasonId: str | None = None
    SeasonName: str | None = None
    DateModified: str | None = None
    FileName: str | None = None


@dataclass
class DataSet:
    Items: List[Item]
