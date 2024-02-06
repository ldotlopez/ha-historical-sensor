# Copyright (C) 2021-2023 Luis López <luis@cuarentaydos.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.


from math import ceil

MIN_REQ_MAJOR_VERSION = 2023
MIN_REQ_MINOR_VERSION = 6

HOMEASSISTANT_INTERNAL_UPDATE_SECONDS = 30
DELAY_ON_MISSING_STATES_METADATA = ceil(HOMEASSISTANT_INTERNAL_UPDATE_SECONDS * 1.1)
