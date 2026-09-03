"""Parser mínimo de Portable Executable (PE) em Python puro.

Precisamos apenas da tabela de *exports* e da tradução RVA→offset de arquivo,
para comparar os bytes de uma função na imagem em disco com os bytes na
memória do processo (Estágio B — detecção de detour inline no opengl32.dll).

Suporta PE32 e PE32+ (32/64 bits), o suficiente para o alcance do anti-cheat
(laboratório CS 1.6 é 32 bits, mas mantemos os dois por robustez).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

IMAGE_DOS_SIGNATURE = 0x5A4D            # "MZ"
IMAGE_NT_SIGNATURE = 0x00004550         # "PE\0\0"

# Directory entry para a tabela de exports
IMAGE_DIRECTORY_ENTRY_EXPORT = 0


@dataclass
class ExportEntry:
    name: str
    rva: int


class PeImage:
    """Imagem PE aberta a partir de bytes do arquivo em disco."""

    def __init__(self, data: bytes):
        self.data = data
        self.image_base = 0
        self.is_64 = False
        self._sections: list[tuple[int, int, int, int]] = []  # (va, vsize, ptr, rawsize)
        self._export_rva = 0
        self._export_size = 0
        self._parse()

    # ------------------------------------------------------------------
    def _parse(self) -> None:
        if len(self.data) < 0x40:
            raise ValueError("arquivo muito curto")

        # assinatura DOS
        if struct.unpack_from("<H", self.data, 0)[0] != IMAGE_DOS_SIGNATURE:
            raise ValueError("não é um arquivo PE (sem assinatura MZ)")

        e_lfanew = struct.unpack_from("<I", self.data, 0x3C)[0]
        if e_lfanew + 24 > len(self.data):
            raise ValueError("e_lfanew inválido")

        # assinatura NT
        if struct.unpack_from("<I", self.data, e_lfanew)[0] != IMAGE_NT_SIGNATURE:
            raise ValueError("não é um arquivo PE (sem assinatura NT)")

        file_header = e_lfanew + 4
        num_sections = struct.unpack_from("<H", self.data, file_header + 2)[0]
        opt_header = file_header + 20
        magic = struct.unpack_from("<H", self.data, opt_header)[0]
        self.is_64 = magic == 0x20B

        # DataDirectory começa em:
        #   PE32 : opt_header + 96
        #   PE32+: opt_header + 112
        dd_offset = opt_header + (112 if self.is_64 else 96)

        if self.is_64:
            # PE32+: ImageBase no offset +24 (8 bytes)
            self.image_base = struct.unpack_from("<Q", self.data, opt_header + 24)[0]
        else:
            # PE32 : ImageBase no offset +28 (4 bytes)
            self.image_base = struct.unpack_from("<I", self.data, opt_header + 28)[0]

        # diretório de exports
        if dd_offset + IMAGE_DIRECTORY_ENTRY_EXPORT * 8 + 8 <= len(self.data):
            self._export_rva, self._export_size = struct.unpack_from(
                "<II", self.data, dd_offset + IMAGE_DIRECTORY_ENTRY_EXPORT * 8
            )

        # tabela de seções
        sec_start = dd_offset + (112 if self.is_64 else 96) + \
            (16 if self.is_64 else 0)
        # IMAGE_OPTIONAL_HEADER32 size = 224, 64 = 240; data dirs = 16*8 each.
        # O bloco de DataDirectory em PE32 tem 16 entradas * 8 = 128; em PE32+ idem.
        # Ajustamos: Número de RVA e tamanhos já consumimos; a tabela de seções
        # começa imediatamente após o fim dos data directories.
        num_dirs = struct.unpack_from("<I", self.data, opt_header + (108 if self.is_64 else 92))[0]
        dir_entries = (num_dirs if num_dirs < 16 else 16) * 8
        section_table = dd_offset + dir_entries

        for i in range(num_sections):
            base = section_table + i * 40
            if base + 40 > len(self.data):
                break
            vsize = struct.unpack_from("<I", self.data, base + 8)[0]
            va = struct.unpack_from("<I", self.data, base + 12)[0]
            rawsize = struct.unpack_from("<I", self.data, base + 16)[0]
            rawptr = struct.unpack_from("<I", self.data, base + 20)[0]
            self._sections.append((va, vsize, rawptr, rawsize))

    # ------------------------------------------------------------------
    def rva_to_offset(self, rva: int) -> int:
        """Traduz um RVA para o offset no arquivo em disco (ou -1)."""
        for va, vsize, rawptr, rawsize in self._sections:
            if va <= rva < va + max(vsize, rawsize):
                delta = rva - va
                if delta < rawsize:
                    return rawptr + delta
                return -1
        return -1

    # ------------------------------------------------------------------
    def exports(self) -> list[ExportEntry]:
        """Devolve a lista de (nome, rva) dos exports nomeados."""
        out: list[ExportEntry] = []

        if self._export_rva == 0:
            return out

        exp_off = self.rva_to_offset(self._export_rva)
        if exp_off < 0 or exp_off + 40 > len(self.data):
            return out

        # IMAGE_EXPORT_DIRECTORY
        nfuncs = struct.unpack_from("<I", self.data, exp_off + 20)[0]
        nnames = struct.unpack_from("<I", self.data, exp_off + 24)[0]
        addr_funcs = struct.unpack_from("<I", self.data, exp_off + 28)[0]
        addr_names = struct.unpack_from("<I", self.data, exp_off + 32)[0]
        addr_ords = struct.unpack_from("<I", self.data, exp_off + 36)[0]

        funcs_off = self.rva_to_offset(addr_funcs)
        names_off = self.rva_to_offset(addr_names)
        ords_off = self.rva_to_offset(addr_ords)

        if funcs_off < 0 or names_off < 0 or ords_off < 0:
            return out

        for i in range(nnames):
            name_rva = struct.unpack_from("<I", self.data, names_off + i * 4)[0]
            name_off = self.rva_to_offset(name_rva)
            if name_off < 0:
                continue
            # lê string até o nulo
            end = self.data.find(b"\x00", name_off)
            if end < 0:
                name = self.data[name_off:].decode("ascii", "ignore").strip("\x00")
            else:
                name = self.data[name_off:end].decode("ascii", "ignore")
            if not name:
                continue
            ord_idx = struct.unpack_from("<H", self.data, ords_off + i * 2)[0]
            if ord_idx >= nfuncs:
                continue
            func_rva = struct.unpack_from("<I", self.data, funcs_off + ord_idx * 4)[0]
            # pontos para dentro de uma seção de código (não forwarder) apenas
            if func_rva != 0 and self.rva_to_offset(func_rva) >= 0:
                out.append(ExportEntry(name, func_rva))

        return out

    # ------------------------------------------------------------------
    @classmethod
    def from_file(cls, path: str) -> "PeImage | None":
        try:
            with open(path, "rb") as fp:
                return cls(fp.read())
        except (OSError, ValueError):
            return None
