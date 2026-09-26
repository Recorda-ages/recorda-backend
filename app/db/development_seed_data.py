"""Deterministic fixtures used by the development database seed."""

from dataclasses import dataclass
from typing import Literal

MediaType = Literal["PHOTO", "VIDEO"]
FollowStatus = Literal["ACCEPTED", "PENDING"]


@dataclass(frozen=True)
class TrackSeed:
    deezer_track_id: str
    title: str
    artist_id: str
    artist_name: str
    artist_image_url: str
    cover_url: str


@dataclass(frozen=True)
class UserSeed:
    username: str
    email: str
    name: str
    profile_picture_url: str
    favorite_track: str
    genres: tuple[str, ...]
    favorite_artists: tuple[str, ...]
    is_private: bool = False


@dataclass(frozen=True)
class RecordaSeed:
    key: str
    username: str
    media_url: str
    media_type: MediaType
    description: str
    track: str
    age_days: int


@dataclass(frozen=True)
class FollowSeed:
    follower: str
    following: str
    status: FollowStatus = "ACCEPTED"


@dataclass(frozen=True)
class CommentSeed:
    key: str
    username: str
    recorda: str
    content: str


TRACKS = {
    "yellow": TrackSeed(
        deezer_track_id="3128096",
        title="Yellow",
        artist_id="892",
        artist_name="Coldplay",
        artist_image_url="https://cdn-images.dzcdn.net/images/artist/3087954bca22f306324912e5ac8375c3/250x250-000000-80-0-0.jpg",
        cover_url="https://cdn-images.dzcdn.net/images/cover/970dce98eeea6729244c0ae71707a83d/500x500-000000-80-0-0.jpg",
    ),
    "harder_better": TrackSeed(
        deezer_track_id="3135556",
        title="Harder, Better, Faster, Stronger",
        artist_id="27",
        artist_name="Daft Punk",
        artist_image_url="https://cdn-images.dzcdn.net/images/artist/638e69b9caaf9f9f3f8826febea7b543/250x250-000000-80-0-0.jpg",
        cover_url="https://cdn-images.dzcdn.net/images/cover/5718f7c81c27e0b2417e2a4c45224f8a/500x500-000000-80-0-0.jpg",
    ),
    "levitating": TrackSeed(
        deezer_track_id="1124841682",
        title="Levitating",
        artist_id="8706544",
        artist_name="Dua Lipa",
        artist_image_url="https://cdn-images.dzcdn.net/images/artist/877872aaf75694f11d53c318700ab2b5/250x250-000000-80-0-0.jpg",
        cover_url="https://cdn-images.dzcdn.net/images/cover/f8364f090ba04f1b19b381ec0390f3e4/500x500-000000-80-0-0.jpg",
    ),
    "blinding_lights": TrackSeed(
        deezer_track_id="908604612",
        title="Blinding Lights",
        artist_id="4050205",
        artist_name="The Weeknd",
        artist_image_url="https://cdn-images.dzcdn.net/images/artist/581693b4724a7fcfa754455101e13a44/250x250-000000-80-0-0.jpg",
        cover_url="https://cdn-images.dzcdn.net/images/cover/fd00ebd6d30d7253f813dba3bb1c66a9/500x500-000000-80-0-0.jpg",
    ),
    "andar_com_fe": TrackSeed(
        deezer_track_id="876104422",
        title="Andar com fé",
        artist_id="2077",
        artist_name="Gilberto Gil",
        artist_image_url="https://cdn-images.dzcdn.net/images/artist/1155049990857b7e5260f2f99a2d48dd/250x250-000000-80-0-0.jpg",
        cover_url="https://cdn-images.dzcdn.net/images/cover/cddf140873af8d2a3512e5e21c70bc34/500x500-000000-80-0-0.jpg",
    ),
    "nao_quero_dinheiro": TrackSeed(
        deezer_track_id="543139482",
        title="Não Quero Dinheiro (Só Quero Amar)",
        artist_id="13704",
        artist_name="Tim Maia",
        artist_image_url="https://cdn-images.dzcdn.net/images/artist/fa32f3688e3b5901b7588020b0377623/250x250-000000-80-0-0.jpg",
        cover_url="https://cdn-images.dzcdn.net/images/cover/8aa8859d166a8a4ab4335bff6796b244/500x500-000000-80-0-0.jpg",
    ),
    "ainda_bem": TrackSeed(
        deezer_track_id="950812822",
        title="Ainda Bem",
        artist_id="13523",
        artist_name="Marisa Monte",
        artist_image_url="https://cdn-images.dzcdn.net/images/artist/4da4e950a642d21a32c0d6ae32d31c4d/250x250-000000-80-0-0.jpg",
        cover_url="https://cdn-images.dzcdn.net/images/cover/745738969ea23df2e6d66a8827254f9e/500x500-000000-80-0-0.jpg",
    ),
    "ceu_azul": TrackSeed(
        deezer_track_id="1509938122",
        title="Céu Azul",
        artist_id="8691",
        artist_name="Charlie Brown Jr.",
        artist_image_url="https://cdn-images.dzcdn.net/images/artist/1a2e562dde23cdbd9abea4bae13eb4fc/250x250-000000-80-0-0.jpg",
        cover_url="https://cdn-images.dzcdn.net/images/cover/e7878aaa78c4d0d00a15ff43f4229b89/500x500-000000-80-0-0.jpg",
    ),
    "tempo_perdido": TrackSeed(
        deezer_track_id="3530724",
        title="Tempo Perdido",
        artist_id="15810",
        artist_name="Legião Urbana",
        artist_image_url="https://cdn-images.dzcdn.net/images/artist/27331b5535cf5a8fd0cece324c201a18/250x250-000000-80-0-0.jpg",
        cover_url="https://cdn-images.dzcdn.net/images/cover/b4738becedbed0481ac71cee50b18d6b/500x500-000000-80-0-0.jpg",
    ),
    "dona_de_mim": TrackSeed(
        deezer_track_id="487611532",
        title="Dona de mim",
        artist_id="262833",
        artist_name="IZA",
        artist_image_url="https://cdn-images.dzcdn.net/images/artist/fd74f81cf7ebf8182d8b469cebf19396/250x250-000000-80-0-0.jpg",
        cover_url="https://cdn-images.dzcdn.net/images/cover/a8a284ab7b2eb270f3c62ed0af6c3039/500x500-000000-80-0-0.jpg",
    ),
}


USERS = (
    UserSeed(
        "gabriel",
        "gabriel@recorda.com",
        "Gabriel Reis",
        "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=400&q=80",
        "harder_better",
        ("Eletrônica / Dance", "Pop", "Rock"),
        ("harder_better", "yellow", "levitating"),
    ),
    UserSeed(
        "ana",
        "ana@recorda.dev",
        "Ana Clara",
        "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=400&q=80",
        "ainda_bem",
        ("MPB", "Pop", "Samba / Pagode"),
        ("ainda_bem", "andar_com_fe", "nao_quero_dinheiro"),
    ),
    UserSeed(
        "lucas",
        "lucas@recorda.dev",
        "Lucas Almeida",
        "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=400&q=80",
        "yellow",
        ("Rock", "Pop", "Eletrônica / Dance"),
        ("yellow", "tempo_perdido", "harder_better"),
    ),
    UserSeed(
        "marina",
        "marina@recorda.dev",
        "Marina Souza",
        "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80",
        "levitating",
        ("Pop", "R&B / Soul", "Eletrônica / Dance"),
        ("levitating", "dona_de_mim", "blinding_lights"),
        is_private=True,
    ),
    UserSeed(
        "pedro",
        "pedro@recorda.dev",
        "Pedro Henrique",
        "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=400&q=80",
        "ceu_azul",
        ("Rock", "Reggae", "Hip Hop / Rap"),
        ("ceu_azul", "tempo_perdido", "yellow"),
    ),
    UserSeed(
        "julia",
        "julia@recorda.dev",
        "Júlia Martins",
        "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=400&q=80",
        "dona_de_mim",
        ("Pop", "R&B / Soul", "MPB"),
        ("dona_de_mim", "ainda_bem", "levitating"),
    ),
    UserSeed(
        "rafael",
        "rafael@recorda.dev",
        "Rafael Costa",
        "https://images.unsplash.com/photo-1507591064344-4c6ce005b128?auto=format&fit=crop&w=400&q=80",
        "tempo_perdido",
        ("Rock", "MPB", "Blues"),
        ("tempo_perdido", "ceu_azul", "andar_com_fe"),
    ),
    UserSeed(
        "camila",
        "camila@recorda.dev",
        "Camila Rocha",
        "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=400&q=80",
        "blinding_lights",
        ("Pop", "R&B / Soul", "Eletrônica / Dance"),
        ("blinding_lights", "dona_de_mim", "levitating"),
        is_private=True,
    ),
    UserSeed(
        "bruno",
        "bruno@recorda.dev",
        "Bruno Oliveira",
        "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?auto=format&fit=crop&w=400&q=80",
        "nao_quero_dinheiro",
        ("MPB", "Funk", "Samba / Pagode"),
        ("nao_quero_dinheiro", "andar_com_fe", "ainda_bem"),
    ),
    UserSeed(
        "beatriz",
        "beatriz@recorda.dev",
        "Beatriz Lima",
        "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=400&q=80",
        "andar_com_fe",
        ("MPB", "Samba / Pagode", "Forró"),
        ("andar_com_fe", "ainda_bem", "nao_quero_dinheiro"),
    ),
)


RECORDAS = (
    RecordaSeed(
        "gabriel-trilha",
        "gabriel",
        "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=85",
        "PHOTO",
        "Uma trilha, uma vista incrível e a música certa.",
        "harder_better",
        1,
    ),
    RecordaSeed(
        "gabriel-viagem",
        "gabriel",
        "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
        "VIDEO",
        "Alguns segundos de uma viagem que merece ser lembrada.",
        "yellow",
        8,
    ),
    RecordaSeed(
        "ana-praia",
        "ana",
        "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?auto=format&fit=crop&w=1200&q=85",
        "PHOTO",
        "Fim de tarde com pessoas queridas.",
        "ainda_bem",
        2,
    ),
    RecordaSeed(
        "ana-cafe",
        "ana",
        "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?auto=format&fit=crop&w=1200&q=85",
        "PHOTO",
        "Café, conversa e uma playlist brasileira.",
        "andar_com_fe",
        13,
    ),
    RecordaSeed(
        "lucas-montanha",
        "lucas",
        "https://images.unsplash.com/photo-1493246507139-91e8fad9978e?auto=format&fit=crop&w=1200&q=85",
        "PHOTO",
        "Subir vale a pena quando a vista é assim.",
        "yellow",
        3,
    ),
    RecordaSeed(
        "lucas-estrada",
        "lucas",
        "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=1200&q=85",
        "PHOTO",
        "Pé na estrada e nenhum plano rígido.",
        "tempo_perdido",
        17,
    ),
    RecordaSeed(
        "marina-show",
        "marina",
        "https://media.w3.org/2010/05/sintel/trailer.mp4",
        "VIDEO",
        "A energia desse momento ficou guardada aqui.",
        "levitating",
        4,
    ),
    RecordaSeed(
        "marina-cidade",
        "marina",
        "https://images.unsplash.com/photo-1518005020951-eccb494ad742?auto=format&fit=crop&w=1200&q=85",
        "PHOTO",
        "Luzes da cidade depois de um dia longo.",
        "blinding_lights",
        19,
    ),
    RecordaSeed(
        "pedro-skate",
        "pedro",
        "https://images.unsplash.com/photo-1520045892732-304bc3ac5d8e?auto=format&fit=crop&w=1200&q=85",
        "PHOTO",
        "Tarde de skate com a melhor trilha sonora.",
        "ceu_azul",
        5,
    ),
    RecordaSeed(
        "pedro-mar",
        "pedro",
        "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=85",
        "PHOTO",
        "Mar calmo e cabeça leve.",
        "yellow",
        21,
    ),
    RecordaSeed(
        "julia-amigas",
        "julia",
        "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?auto=format&fit=crop&w=1200&q=85",
        "PHOTO",
        "Rir até perder a hora com elas.",
        "dona_de_mim",
        6,
    ),
    RecordaSeed(
        "julia-flores",
        "julia",
        "https://images.unsplash.com/photo-1490750967868-88aa4486c946?auto=format&fit=crop&w=1200&q=85",
        "PHOTO",
        "Um pouco de cor para guardar o dia.",
        "ainda_bem",
        23,
    ),
    RecordaSeed(
        "rafael-violao",
        "rafael",
        "https://images.unsplash.com/photo-1510915361894-db8b60106cb1?auto=format&fit=crop&w=1200&q=85",
        "PHOTO",
        "Ensaio improvisado que virou memória.",
        "tempo_perdido",
        7,
    ),
    RecordaSeed(
        "rafael-parque",
        "rafael",
        "https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=1200&q=85",
        "PHOTO",
        "Domingo sem pressa no parque.",
        "andar_com_fe",
        25,
    ),
    RecordaSeed(
        "camila-noite",
        "camila",
        "https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=1200&q=85",
        "PHOTO",
        "A cidade muda quando a noite chega.",
        "blinding_lights",
        9,
    ),
    RecordaSeed(
        "camila-danca",
        "camila",
        "https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?auto=format&fit=crop&w=1200&q=85",
        "PHOTO",
        "Dançar sem pensar no relógio.",
        "levitating",
        26,
    ),
    RecordaSeed(
        "bruno-churrasco",
        "bruno",
        "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=1200&q=85",
        "PHOTO",
        "Almoço de domingo com a família reunida.",
        "nao_quero_dinheiro",
        10,
    ),
    RecordaSeed(
        "bruno-vinil",
        "bruno",
        "https://images.unsplash.com/photo-1461360228754-6e81c478b882?auto=format&fit=crop&w=1200&q=85",
        "PHOTO",
        "Garimpo de vinil e boas descobertas.",
        "ainda_bem",
        27,
    ),
    RecordaSeed(
        "beatriz-festival",
        "beatriz",
        "https://images.unsplash.com/photo-1501386761578-eac5c94b800a?auto=format&fit=crop&w=1200&q=85",
        "PHOTO",
        "Música ao vivo e um dia inesquecível.",
        "andar_com_fe",
        11,
    ),
    RecordaSeed(
        "beatriz-natureza",
        "beatriz",
        "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=1200&q=85",
        "PHOTO",
        "Respirar fundo e ouvir a natureza.",
        "nao_quero_dinheiro",
        29,
    ),
)


FOLLOWS = (
    FollowSeed("gabriel", "ana"),
    FollowSeed("gabriel", "lucas"),
    FollowSeed("gabriel", "marina"),
    FollowSeed("gabriel", "pedro"),
    FollowSeed("gabriel", "camila", "PENDING"),
    FollowSeed("ana", "gabriel"),
    FollowSeed("ana", "lucas"),
    FollowSeed("ana", "julia"),
    FollowSeed("lucas", "gabriel"),
    FollowSeed("lucas", "marina"),
    FollowSeed("lucas", "pedro"),
    FollowSeed("marina", "ana"),
    FollowSeed("marina", "julia"),
    FollowSeed("marina", "beatriz"),
    FollowSeed("pedro", "gabriel"),
    FollowSeed("pedro", "rafael"),
    FollowSeed("pedro", "bruno"),
    FollowSeed("julia", "ana"),
    FollowSeed("julia", "camila"),
    FollowSeed("julia", "beatriz"),
    FollowSeed("rafael", "pedro"),
    FollowSeed("rafael", "bruno"),
    FollowSeed("rafael", "gabriel"),
    FollowSeed("camila", "marina", "PENDING"),
    FollowSeed("camila", "julia"),
    FollowSeed("bruno", "beatriz"),
    FollowSeed("bruno", "gabriel"),
    FollowSeed("beatriz", "ana"),
    FollowSeed("beatriz", "rafael"),
)


COMMENTS = (
    CommentSeed("c01", "ana", "gabriel-trilha", "Que vista linda!"),
    CommentSeed("c02", "lucas", "gabriel-viagem", "Essa música combinou muito."),
    CommentSeed("c03", "gabriel", "ana-praia", "Esse fim de tarde ficou incrível."),
    CommentSeed("c04", "julia", "ana-cafe", "Saudade de um café assim."),
    CommentSeed("c05", "marina", "lucas-montanha", "Quero conhecer esse lugar!"),
    CommentSeed("c06", "pedro", "lucas-estrada", "A melhor parte é ir sem roteiro."),
    CommentSeed("c07", "ana", "marina-show", "Energia maravilhosa!"),
    CommentSeed("c08", "beatriz", "marina-cidade", "As luzes ficaram lindas."),
    CommentSeed("c09", "rafael", "pedro-skate", "Mandou muito nessa foto."),
    CommentSeed("c10", "camila", "pedro-mar", "Paz em forma de imagem."),
    CommentSeed("c11", "beatriz", "julia-amigas", "Esse dia foi especial!"),
    CommentSeed("c12", "bruno", "julia-flores", "As cores ficaram perfeitas."),
    CommentSeed("c13", "lucas", "rafael-violao", "Quando sai o próximo ensaio?"),
    CommentSeed("c14", "gabriel", "rafael-parque", "Domingo bem aproveitado."),
    CommentSeed("c15", "julia", "camila-noite", "A trilha perfeita para essa foto."),
    CommentSeed("c16", "marina", "camila-danca", "Essa noite foi inesquecível."),
    CommentSeed("c17", "pedro", "bruno-churrasco", "Já quero o próximo!"),
    CommentSeed("c18", "rafael", "bruno-vinil", "Ótima descoberta musical."),
    CommentSeed("c19", "camila", "beatriz-festival", "Que vontade de voltar."),
    CommentSeed("c20", "ana", "beatriz-natureza", "Lugar perfeito para respirar."),
)
