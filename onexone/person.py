#!/usr/bin/env python
#
# person - Representation of a person, part of onexone
#
# Copyright (C) 2018 Michael Davies <michael@the-davies.net>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#

import six.moves as sm
import prettytable

from onexone import command
from onexone import datastore
from onexone import debugging
from onexone import utils


class Person:
    """Representation of a person."""

    _ES_ENABLE = 'enable'
    _ES_DISABLE = 'disable'

    def __init__(self):
        self.c = command.CommandOptions('person')
        self.c.add_command('list', self.list, "[all | disabled | enabled]")
        self.c.add_command('add', self.add, "<first> <last> <role>"
                           "<start-date> [end-date]")
        self.c.add_command('edit', self.edit, "<searchstr> <key> <value>")
        self.c.add_command('delete', self.delete, "(<first> <last>|<nick>)")
        self.c.add_command('find', self.find, "<search-string>")
        self.c.add_command('info', self.info, "<search-string>")

    @debugging.trace
    def _search(self, field, value):
        """Search for all persons that have 'field' set to 'value'

        :param field: the field to search for
        :param value: the value we're looking for
        :returns: The set of persons that meet the criteria, None otherwise
        """
        ds = datastore.get_datastore()
        return ds.find(field, value)

    @debugging.trace
    def _find(self, searchstr, interactive=False):
        """Search for a person based upon name, matching against the supplied
        string search criteria.

        :param searchstr: the search string to find a name match against
        :param interactive: not used
        :returns: The list of persons that match
        """
        results = set()

        result = self._search('first_name', searchstr)
        if result:
            for r in result:
                results.add(r)

        result = self._search('last_name', searchstr)
        if result:
            for r in result:
                results.add(r)

        # Search against fullname as well
        all_fullnames = datastore.get_datastore().get_all_fullnames()
        for fullname in all_fullnames:
            if searchstr in fullname:
                results.add(fullname)

        return list(results)

    @debugging.trace
    def find_person(self, person_str):
        """Search for a person based upon the supplied search string.

        :param person_str: the search criteria
        :returns: Tuple (Bool, result set | reason)
        """

        # Note(mrda): Method not yet used
        possible_persons = self._find(person_str)
        len_possible_persons = len(possible_persons)
        if len_possible_persons == 0:
            return (False, "No match found")
        elif len_possible_persons != 1:
            return (False, "No unique match found")
        else:
            return (True, possible_persons[0])

    @debugging.trace
    def _exact_match(self, first, last):
        """Determine if there is an exact person match based upon the supplied
        search criteria.

        :param first: the first name to search against
        :param last: the last name to search against
        :returns: Return True if it's an exact match
        """

        first_result = self._search('first_name', first)
        if not first_result:
            return False

        last_result = self._search('last_name', last)
        if not last_result:
            return False

        intersection = [v for v in first_result if v in last_result]

        return len(intersection) == 1

    @debugging.trace
    def edit(self, args):
        """Top level person edit function.  Look for a person based upon the
        provided search criteria, and allow fields to be updated.

        :param args: The criteria to search against, and key/value updates.
        """
        if len(args) != 3:
            self.c.display_usage('edit')
            return

        searchstr = args[0]
        key = args[1]
        val = args[2]

        exact, fullname = self.find_person(searchstr)
        if not exact:
            print("*** '{}' does not exactly match a single person. "
                  "Possibilities are:".format(searchstr))
            self.find([searchstr])
            return

        ds = datastore.get_datastore()
        ds.update_person(fullname, key, val)

    @debugging.trace
    def find(self, args):
        """Top level person find function.  Look for a person based upon the
        provided search criteria.  Print the results.

        :param args: The criteria to search against
        """
        if len(args) != 1:
            self.c.display_usage('find')
            return

        results = self._find(args[0], True)
        if results:
            print("\n".join(results))
        else:
            print("No match found")

    @debugging.trace
    def info(self, args, interactive=True):
        """Top level info command.  Find a person based up on the supplied
        criteria, and print all relevant information.

        :param args: the criteria to check
        """
        if len(args) != 1:
            self.c.display_usage('info')
            return

        searchstr = args[0]
        if interactive:
            print("Searching for {}".format(searchstr))
        fullnames = self._find(searchstr, True)
        if not fullnames:
            if interactive:
                print("No record found")
            return
        for f in fullnames:
            self._print_person(f)
        print("")

    @debugging.trace
    def _print_person(self, fullname):
        """Print all information about a person.

        :param fullname: The person to print info about
        """
        ds = datastore.get_datastore()
        start_date, end_date = ds.get_dates(fullname)
        print("")
        print("First name: {}".format(ds.get_first_name(fullname)))
        print("Last name: {}".format(ds.get_last_name(fullname)))
        print("Role: {}".format(ds.get_role(fullname)))
        print("Start Date: {}".format(start_date))
        print("End Date: {}".format(end_date))
        print("Enabled?: {}".format(ds.is_enabled(fullname)))
        print("One-on-One Meetings:")
        for meeting in sorted(ds.get_meetings(fullname)):
            print("  {}".format(meeting))

    @debugging.trace
    def add(self, args):
        """Top level function for adding a person.

        :param args: list of arguments to use in building a person
        """
        len_args = len(args)
        if len_args < 4 or len_args > 5:
            self.c.display_usage('add')
            return

        end_date = ""

        if len_args == 4:
            first, last, role, start_date = args
        elif len_args == 5:
            first, last, role, start_date, end_date = args

        ds = datastore.get_datastore()
        fullname = ds.build_fullname(first, last)
        if ds.person_exists(fullname):
            print("*** Person '{}' already exists, no changes made".format
                  (fullname))
            return

        ds.new_person(first, last, role, start_date, end_date)

    @debugging.trace
    def delete(self, args):
        """Top level function for deleting a person.

        :param args: list to use in identifying the person to delete
        """
        len_args = len(args)
        if len_args < 1 or len_args > 2:
            self.c.display_usage('delete')
            return

        ds = datastore.get_datastore()

        fullname = None
        if len_args == 1:
            # Partial user supplied, go find a match
            fullnames = self._find(args[0])
            if len(fullnames) == 0:
                print("Couldn't find person '{}' to delete".format(args[0]))
                return
            elif len(fullnames) != 1:
                print("Multiple matches, won't delete {}".format(
                      " and ".join(fullnames[0])))
                return
            fullname = fullnames[0]
        else:
            # Provided a first and last name, looking for an exact match
            first, last = args
            if self._exact_match(first, last):
                fullname = ds.build_fullname(first, last)

        if sm.input("Are you sure you want to delete '{}'? ".
                    format(fullname)) not in ['Y', 'y']:
            print("Not deleting user")
            return

        ds.remove_entry(fullname)

    @debugging.trace
    def list(self, args):
        """Top level function for listing persons.

        :param args: list to use in identifying what to list
        """
        len_args = len(args)

        ds = datastore.get_datastore()
        if len_args == 0:
            fullnames = ds.list_fullnames()
            if fullnames is not None:
                print("\n".join(ds.list_fullnames()))
        elif len_args == 1 and args[0] == 'all':
            self.list_everything()
        elif len_args == 1 and args[0] == 'enabled':
            self.list_everything(enable_state=self._ES_ENABLE)
        elif len_args == 1 and args[0] == 'disabled':
            self.list_everything(enable_state=self._ES_DISABLE)
        else:
            self.c.display_usage('list')

    @debugging.trace
    def list_everything(self, enable_state=None):
        """List everything about all people."""
        ds = datastore.get_datastore()
        table = prettytable.PrettyTable()

        def _get_headings():
            a = []
            a.append("First Name")
            a.append("Last Name")
            a.append("Role")
            a.append("Start Date")
            if enable_state != self._ES_ENABLE:
                a.append("End Date")
            a.append("Meetings")
            return a

        def _sanitise(a):
            # Cleanup printing by not printing None or True
            if a is None or a is True:
                return ""
            else:
                return a

        def _print_person(fullname):
            a = []
            a.append(_sanitise(ds.get_first_name(fullname)))
            a.append(_sanitise(ds.get_last_name(fullname)))
            a.append(_sanitise(ds.get_role(fullname)))
            dates = ds.get_dates(fullname)
            a.append(utils.format_string(_sanitise(dates[0])))
            if enable_state != self._ES_ENABLE:
                a.append(utils.format_string(_sanitise(dates[1])))
            meetings = ds.get_meetings(fullname)
            if len(meetings) < 2:
                a.append(", ".join(utils.format_string(m) for m in meetings))
            else:
                a.append("{} ... {}".format(
                    utils.format_string(meetings[0]),
                    utils.format_string(meetings[-1])))
            table.add_row(a)

        headings = _get_headings()
        table.field_names = headings
        for h in headings:
            table.align[h] = 'l'  # left align
        ds.iterate_over_persons(_print_person, enable_state)
        print(table)

    @debugging.trace
    def parse(self, args):
        """Top level function to parse arguments given to the person command.
        If the person sub-command isn't recognised, print out usage.  Note that
        this command is only meant to be invoked from higher level parsing
        function.
        """
        try:
            if len(args) == 0:
                self.c.usage()
                return
            self.c.jump(args)
        except Exception as e:
            print("*** Unexpected exception in person.parse: {}".format(e))
